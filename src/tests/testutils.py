import shutil
import subprocess
import sys
import unittest
import platform
from builtins import ValueError
from pathlib import Path
from tempfile import mkdtemp
from unittest.case import TestCase

from _io import StringIO
from leaf import __version__
from leaf.__main__ import runLeaf
from leaf.api import RelengManager
from leaf.core.constants import JsonConstants, LeafFiles, LeafSettings
from leaf.core.jsonutils import jsonLoadFile, jsonWriteFile
from leaf.core.settings import Setting
from leaf.model.package import Manifest, PackageIdentifier

LeafSettings.NON_INTERACTIVE.value = 1

TestCase.maxDiff = None
LEAF_UT_DEBUG = Setting("LEAF_UT_DEBUG")
LEAF_UT_SKIP = Setting("LEAF_UT_SKIP", "")
LEAF_UT_CREATE_TEMPLATE = Setting("LEAF_UT_CREATE_TEMPLATE")

PROJECT_ROOT_FOLDER = Path(__file__).parent.parent.parent
RESOURCE_FOLDER = PROJECT_ROOT_FOLDER / "src/tests/resources"
EXPECTED_OUTPUT_FOLDER = PROJECT_ROOT_FOLDER / "src/tests/expected_ouput"
PLUGINS_FOLDER = PROJECT_ROOT_FOLDER / "resources/share/leaf/plugins"

TAR_EXTRA_ARGS = {
    PackageIdentifier.fromString("compress-xz_1.0"): ('-z', '.'),
    PackageIdentifier.fromString("compress-bz2_1.0"): ('-j', '.'),
    PackageIdentifier.fromString("compress-gz_1.0"): ('-J', '.')
}
ALT_INDEX_CONTENT = {
    "multitags_1.0": True,
    "version_2.0": False,
    "upgrade_1.2": False,
    "upgrade_2.0": False
}

TEST_GPG_FINGERPRINT = "E35D6817397359074160F68952ECE808A2BC372C"
TEST_GPG_HOMEDIR = PROJECT_ROOT_FOLDER / 'src/tests/gpg'


class StringIOWrapper(StringIO):

    def __init__(self, stream, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.__altstream__ = stream

    def write(self, txt):
        super().write(txt)
        self.__altstream__.write(txt)

    @property
    def encoding(self):
        return self.__altstream__.encoding

    @encoding.setter
    def encoding(self, enc):
        self.__altstream__.encoding = enc


class ContentChecker():

    def __init__(self, tester, testCase, templateOut=None, templateErr=[], variables=None, byMethod=True):
        self.tester = tester
        self.testCase = testCase
        self.templateOut, self.templateErr = templateOut, templateErr
        self.variables = variables
        self.sysstdout = sys.stdout
        self.sysstderr = sys.stderr
        self.stdoutWrapper = StringIOWrapper(self.sysstdout)
        self.stderrWrapper = StringIOWrapper(self.sysstderr)
        self.byMethod = byMethod

    def __enter__(self):
        sys.stdout = self.stdoutWrapper
        sys.stderr = self.stderrWrapper

    def __exit__(self, *_):
        sys.stdout = self.sysstdout
        sys.stderr = self.sysstderr
        self._checkContent(self.templateOut, self.stdoutWrapper)
        self._checkContent(self.templateErr, self.stderrWrapper)

    def _checkContent(self, template, stream):
        if template is None:
            # No check
            return

        streamLines = stream.getvalue().splitlines()
        lines = []
        if isinstance(template, str):
            # Template is a file name
            classFolder = EXPECTED_OUTPUT_FOLDER / self.testCase.__class__.__name__
            if self.byMethod:
                template = self.testCase.id().split('.')[-1] + '_' + template
            template = classFolder / template

            # Generate template if envar is set
            if LEAF_UT_CREATE_TEMPLATE.as_boolean():
                if not classFolder.exists():
                    classFolder.mkdir()
                for line in streamLines:
                    line = self._replaceVariables(line, True)
                    lines.append(line)
                with template.open(mode='w') as f:
                    f.write('\n'.join(lines))
                return

            # Read template content
            self.tester.assertTrue(template.exists())
            with open(str(template)) as fp:
                for line in fp.read().splitlines():
                    line = self._replaceVariables(line)
                    lines.append(line)
        else:
            lines = template

        self.tester.assertEqual(
            lines,
            streamLines)

    def _replaceVariables(self, line, reverse=False):
        if self.variables is not None:
            for k, v in self.variables.items():
                k, v = str(k), str(v)
                if reverse:
                    line = line.replace(v, k)
                else:
                    line = line.replace(k, v)
        return line


class LeafTestCase(unittest.TestCase):

    def __init__(self, *args, verbosity=None, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
        self.__verbosity = verbosity

    @property
    def verbosity(self):
        return self.__verbosity

    def setUp(self):
        if self.__verbosity and LEAF_UT_SKIP.is_set():
            if self.__verbosity.lower() in LEAF_UT_SKIP.value.lower():
                self.skipTest("Verbosity %s is ignored" % self.__verbosity)

        print("[LEAF_VERBOSE]  %s  -->  %s" %
              (self.__class__.__name__, self.__verbosity))
        LeafSettings.VERBOSITY.value = self.__verbosity

    def _get_default_variables(self):
        return {
            "{TESTS_LEAF_VERSION}": __version__,
            "{TESTS_PLATFORM_SYSTEM}": platform.system(),
            "{TESTS_PLATFORM_MACHINE}": platform.machine(),
            "{TESTS_PLATFORM_RELEASE}": platform.release(),
            "{TESTS_PROJECT_FOLDER}": PROJECT_ROOT_FOLDER
        }

    def assertStdout(self, templateOut=None, templateErr=[], variables=None, byMethod=True):
        '''
        Possibles values for templates :
        - None -> the stream is not checked
        - Empty list, tuple or set -> the stream is checked as empty
        - File name -> the stream is compared to the file content
        '''
        vars = self._get_default_variables()
        if variables is not None:
            vars.update(variables)
        return ContentChecker(self,
                              testCase=self,
                              templateOut=templateOut,
                              templateErr=templateErr,
                              variables=vars,
                              byMethod=byMethod)


class LeafTestCaseWithRepo(LeafTestCase):

    ROOT_FOLDER = None
    REPO_FOLDER = None
    VOLATILE_FOLDER = None

    @classmethod
    def setUpClass(cls):
        LeafTestCase.setUpClass()

        if LEAF_UT_DEBUG.as_boolean():
            LeafTestCaseWithRepo.ROOT_FOLDER = Path("/tmp/leaf")
        else:
            LeafTestCaseWithRepo.ROOT_FOLDER = Path(
                mkdtemp(prefix="leaf_tests_"))

        LeafTestCaseWithRepo.REPO_FOLDER = LeafTestCaseWithRepo.ROOT_FOLDER / "repository"
        LeafTestCaseWithRepo.VOLATILE_FOLDER = LeafTestCaseWithRepo.ROOT_FOLDER / "volatile"

        shutil.rmtree(str(LeafTestCaseWithRepo.ROOT_FOLDER),
                      ignore_errors=True)

        assert RESOURCE_FOLDER.exists(), "Cannot find resources folder!"
        generateRepo(RESOURCE_FOLDER,
                     LeafTestCaseWithRepo.REPO_FOLDER)

    @classmethod
    def tearDownClass(cls):
        if not LEAF_UT_DEBUG.as_boolean():
            shutil.rmtree(str(LeafTestCaseWithRepo.ROOT_FOLDER), True)

    def setUp(self):
        shutil.rmtree(str(LeafTestCaseWithRepo.VOLATILE_FOLDER),
                      ignore_errors=True)
        LeafTestCaseWithRepo.VOLATILE_FOLDER.mkdir()
        LeafSettings.CONFIG_FOLDER.value = self.getConfigurationFolder()
        LeafSettings.CACHE_FOLDER.value = self.getCacheFolder()

    def _get_default_variables(self):
        out = super()._get_default_variables()
        out.update({
            "{TESTS_WORKSPACE_FOLDER}": self.getWorkspaceFolder(),
            "{TESTS_REMOTE_URL}": self.getRemoteUrl(),
            "{TESTS_REMOTE_URL2}": self.getRemoteUrl2(),
            "{TESTS_INSTALL_FOLDER}": self.getInstallFolder(),
            "{TESTS_CACHE_FOLDER}": self.getCacheFolder()
        })
        return out

    def tearDown(self):
        pass

    def getRemoteUrl(self):
        return (LeafTestCaseWithRepo.REPO_FOLDER / "index.json").as_uri()

    def getRemoteUrl2(self):
        return str(LeafTestCaseWithRepo.REPO_FOLDER / "index2.json")

    def getVolatileItem(self, name, mkdir=True):
        out = LeafTestCaseWithRepo.VOLATILE_FOLDER / name
        if mkdir and not out.is_dir():
            out.mkdir()
        return out

    def getConfigurationFolder(self):
        return self.getVolatileItem("config", mkdir=True)

    def getInstallFolder(self):
        return self.getVolatileItem("packages")

    def getCacheFolder(self):
        return self.getVolatileItem("cache", mkdir=True)

    def getWorkspaceFolder(self):
        return self.getVolatileItem("workspace")

    def getAltWorkspaceFolder(self):
        return self.getVolatileItem("alt-workspace")

    def checkContent(self, content, pisList):
        self.assertEqual(len(content), len(pisList))
        for pis in pisList:
            self.assertTrue(PackageIdentifier.fromString(pis) in content)

    def checkInstalledPackages(self, pisList):
        for pis in pisList:
            folder = self.getInstallFolder() / str(pis)
            self.assertTrue(folder.is_dir(), msg=str(folder))
        folderItemCount = 0
        for i in self.getInstallFolder().iterdir():
            if i.is_dir():
                folderItemCount += 1
        self.assertEqual(len(pisList),
                         folderItemCount)

    def checkCurrentProfile(self, name):
        lnk = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME / \
            LeafFiles.CURRENT_PROFILE_LINKNAME
        if name is None:
            self.assertFalse(lnk.exists())
        else:
            self.assertEqual(name, lnk.resolve().name)

    def checkProfileContent(self, profileName, contentList):
        pfFolder = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME / profileName
        if contentList is None:
            self.assertFalse(pfFolder.exists())
        else:
            self.assertTrue(pfFolder.exists())
            symlinkCount = 0
            for item in pfFolder.iterdir():
                if item.is_symlink():
                    symlinkCount += 1
                self.assertTrue(item.name in contentList,
                                "Unexpected link %s" % item)
            self.assertEqual(symlinkCount, len(contentList))


class LeafTestCaseWithCli(LeafTestCaseWithRepo):

    @classmethod
    def setUpClass(cls):
        LeafTestCaseWithRepo.setUpClass()
        LeafSettings.RESOURCES_FOLDER.value = PLUGINS_FOLDER.parent

    @classmethod
    def tearDownClass(cls):
        LeafTestCaseWithRepo.tearDownClass()

    def _get_default_variables(self):
        out = super()._get_default_variables()
        out.update({
            "{TESTS_RESOURCES_FOLDER}": LeafSettings.RESOURCES_FOLDER.value
        })
        return out

    def setUp(self):
        LeafTestCaseWithRepo.setUp(self)
        self.leafExec("config", "--root", self.getInstallFolder())
        self.leafExec(("remote", "add"), "--insecure",
                      "default", self.getRemoteUrl())
        self.leafExec(("remote", "add"), "--insecure",
                      "other", self.getRemoteUrl2())

    def exec(self, *command, bin="leaf", expectedRc=0):
        cmd = ' '.join(command)
        if bin is not None:
            cmd = bin + ' ' + cmd
        # Mask verbosity if set
        oldVerbosity = LeafSettings.VERBOSITY.value
        try:
            LeafSettings.VERBOSITY.value = None
            rc, stdout = subprocess.getstatusoutput(cmd)
            if expectedRc is not None:
                self.assertEqual(expectedRc, rc)
            return stdout
        finally:
            LeafSettings.VERBOSITY.value = oldVerbosity

    def leafExec(self, verb, *args,
                 altWorkspace=None, expectedRc=0):
        if altWorkspace is None:
            altWorkspace = self.getWorkspaceFolder()

        command = []
        if self.verbosity == "quiet":
            command.append("--quiet")
        elif self.verbosity == "verbose":
            command.append("--verbose")
        command += ("--non-interactive", "--workspace", altWorkspace)
        if isinstance(verb, (list, tuple)):
            command += verb
        else:
            command.append(verb)
        if args is not None:
            command += args
        self.eazyExecute(command, expectedRc)

    def eazyExecute(self, command, expectedRc):
        command = [str(i) for i in command]
        # Mask verbosity if set
        oldVerbosity = LeafSettings.VERBOSITY.value
        try:
            LeafSettings.VERBOSITY.value = None
            out = runLeaf(command)
            if expectedRc is not None:
                self.assertEqual(expectedRc, out, " ".join(command))
            return out
        finally:
            LeafSettings.VERBOSITY.value = oldVerbosity


def generateRepo(sourceFolder, outputFolder):
    if not outputFolder.is_dir():
        outputFolder.mkdir(parents=True)
    artifactsList = []
    artifactsList2 = []

    rm = RelengManager()
    for packageFolder in sourceFolder.iterdir():
        if packageFolder.is_dir() and PackageIdentifier.isValidIdentifier(packageFolder.name):
            manifestFile = packageFolder / LeafFiles.MANIFEST
            if manifestFile.is_file():
                manifest = Manifest.parse(manifestFile)
                if str(manifest.getIdentifier()) != packageFolder.name:
                    raise ValueError("Naming error: %s != %s" % (
                        str(manifest.getIdentifier()), packageFolder.name))
                filename = str(manifest.getIdentifier()) + ".leaf"
                outputFile = outputFolder / filename
                tarExtraArgs = TAR_EXTRA_ARGS.get(manifest.getIdentifier())
                rm.createPackage(
                    packageFolder,
                    outputFile,
                    tarExtraArgs=tarExtraArgs)
                # Check that the generated archive is OK
                checkArchiveFormat(
                    outputFile,
                    tarExtraArgs[0] if tarExtraArgs is not None else None)
                # Create multi index.json
                if str(manifest.getIdentifier()) in ALT_INDEX_CONTENT:
                    artifactsList2.append(outputFile)
                    if ALT_INDEX_CONTENT[str(manifest.getIdentifier())]:
                        artifactsList.append(outputFile)
                else:
                    artifactsList.append(outputFile)
                # Create a problem with failure-badhash package
                if manifest.getName() == "failure-badhash":
                    infoNode = jsonLoadFile(
                        rm._getExternalInfoFile(outputFile))
                    # chosen by fair dice roll.
                    # garanteed to be random.
                    infoNode[JsonConstants.REMOTE_PACKAGE_HASH] = \
                        "sha384:d1083143b5c4cf7f1ddaadc391b2d0102fc9fffeb0951ec51020b512ef9548d40cd1af079a1221133faa949fdc304c41"
                    jsonWriteFile(rm._getExternalInfoFile(
                        outputFile), infoNode, pp=True)

    if len(artifactsList) == 0 or len(artifactsList2) == 0:
        raise ValueError("Empty index!")

    with open(str(outputFolder / "multitags_1.0.leaf.tags"), 'w') as fp:
        fp.write("volatileTag1\n")
        fp.write("volatileTag2")
    rm.generateIndex(outputFolder / "index.json",
                     artifactsList,
                     name="First repository",
                     description="First repository description",
                     prettyprint=True)

    with open(str(outputFolder / "multitags_1.0.leaf.tags"), 'w') as fp:
        fp.write("volatileTag3\n")
        fp.write("volatileTag4")
    rm.generateIndex(outputFolder / "index2.json",
                     artifactsList2,
                     name="Second repository",
                     description="Second repository description",
                     prettyprint=True)

    # Sign with GPG
    subprocess.check_call(["gpg",
                           "--homedir", str(TEST_GPG_HOMEDIR),
                           "--detach-sign", "--armor",
                           str(outputFolder / "index.json")])
    subprocess.check_call(["gpg",
                           "--homedir", str(TEST_GPG_HOMEDIR),
                           "--detach-sign", "--armor",
                           str(outputFolder / "index2.json")])


def checkArchiveFormat(file, compression):
    if compression == "-J":
        checkMime(file, "x-xz")
    elif compression == "-z":
        checkMime(file, "gzip")
    elif compression == "-j":
        checkMime(file, "x-bzip2")
    else:
        checkMime(file, "x-tar")


def checkMime(file, expectedMime):
    mime = subprocess.getoutput("file -bi " + str(file))
    if not mime.startswith("application/" + expectedMime):
        raise ValueError("File %s has invalid mime type %s" % (file, mime))


def getLines(file):
    with open(str(file)) as fp:
        return fp.read().splitlines()


def envFileToMap(envDumpFile):
    out = {}
    with open(str(envDumpFile), "r") as fp:
        for line in fp.read().splitlines():
            i = line.index("=")
            out[line[:i]] = line[i + 1:]
    return out
