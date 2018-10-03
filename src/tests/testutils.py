import os
import shutil
import subprocess
import sys
import unittest
from builtins import ValueError
from pathlib import Path
from tempfile import mkdtemp
from unittest.case import TestCase

from _io import StringIO
from leaf.cli.cli import LeafCli
from leaf.constants import EnvConstants, JsonConstants, LeafFiles
from leaf.core.relengmanager import RelengManager
from leaf.format.logger import Verbosity
from leaf.model.package import Manifest, PackageIdentifier
from leaf.utils import jsonLoadFile, jsonWriteFile


TestCase.maxDiff = None
LEAF_UT_DEBUG = os.environ.get("LEAF_UT_DEBUG")
LEAF_UT_SKIP = os.environ.get("LEAF_UT_SKIP", "")
LEAF_UT_CREATE_TEMPLATE = os.environ.get("LEAF_UT_CREATE_TEMPLATE")

ROOT_FOLDER = Path(__file__).parent.parent.parent
RESOURCE_FOLDER = ROOT_FOLDER / "src" / "tests" / "resources"
EXPECTED_OUTPUT_FOLDER = ROOT_FOLDER / "src" / "tests" / "expected_ouput"
EXTENSIONS_FOLDER = ROOT_FOLDER / "resources" / "bin"

SEPARATOR = "--------------------"
ALT_COMPRESSION = {
    "compress-tar_1.0": 'tar',
    "compress-xz_1.0": 'xz',
    "compress-bz2_1.0": 'bz2',
    "compress-gz_1.0": 'gz'
}

TEST_GPG_FINGERPRINT = "E35D6817397359074160F68952ECE808A2BC372C"
TEST_GPG_HOMEDIR = ROOT_FOLDER / 'src' / 'tests' / 'gpg'


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
            if LEAF_UT_CREATE_TEMPLATE is not None:
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


class AbstractTestWithChecker(unittest.TestCase):

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    def assertStdout(self, templateOut=None, templateErr=[], variables=None, byMethod=True):
        '''
        Possibles values for templates :
        - None -> the stream is not checked
        - Empty list, tuple or set -> the stream is checked as empty
        - File name -> the stream is compared to the file content
        '''
        return ContentChecker(self,
                              testCase=self,
                              templateOut=templateOut,
                              templateErr=templateErr,
                              variables=variables,
                              byMethod=byMethod)


class AbstractTestWithRepo(AbstractTestWithChecker):

    ROOT_FOLDER = None
    REPO_FOLDER = None
    VOLATILE_FOLDER = None

    def __init__(self, methodName):
        AbstractTestWithChecker.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        if LEAF_UT_DEBUG is not None:
            AbstractTestWithRepo.ROOT_FOLDER = Path("/tmp/leaf")
        else:
            AbstractTestWithRepo.ROOT_FOLDER = Path(
                mkdtemp(prefix="leaf_tests_"))

        AbstractTestWithRepo.REPO_FOLDER = AbstractTestWithRepo.ROOT_FOLDER / "repository"
        AbstractTestWithRepo.VOLATILE_FOLDER = AbstractTestWithRepo.ROOT_FOLDER / "volatile"

        shutil.rmtree(str(AbstractTestWithRepo.ROOT_FOLDER),
                      ignore_errors=True)

        assert RESOURCE_FOLDER.exists(), "Cannot find resources folder!"
        generateRepo(RESOURCE_FOLDER,
                     AbstractTestWithRepo.REPO_FOLDER)

    @classmethod
    def tearDownClass(cls):
        if LEAF_UT_DEBUG is None:
            shutil.rmtree(str(AbstractTestWithRepo.ROOT_FOLDER), True)

    def setUp(self):
        shutil.rmtree(str(AbstractTestWithRepo.VOLATILE_FOLDER),
                      ignore_errors=True)
        AbstractTestWithRepo.VOLATILE_FOLDER.mkdir()
        os.environ[EnvConstants.CUSTOM_CONFIG] = str(
            self.getConfigurationFolder())
        os.environ[EnvConstants.CUSTOM_CACHE] = str(
            self.getCacheFolder())

    def tearDown(self):
        pass

    def getRemoteUrl(self):
        return (AbstractTestWithRepo.REPO_FOLDER / "index.json").as_uri()

    def getRemoteUrl2(self):
        return (AbstractTestWithRepo.REPO_FOLDER / "index2.json").as_uri()

    def getVolatileItem(self, name, mkdir=True):
        out = AbstractTestWithRepo.VOLATILE_FOLDER / name
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


class LeafCliWrapper(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.preVerbArgs = []
        self.postVerbArgs = []

    @classmethod
    def setUpClass(cls):
        AbstractTestWithRepo.setUpClass()
        LeafCliWrapper.OLD_PATH = os.environ['PATH']
        assert EXTENSIONS_FOLDER.is_dir()
        os.environ['PATH'] = "%s:%s" % (EXTENSIONS_FOLDER,
                                        LeafCliWrapper.OLD_PATH)
        print("Update PATH:", os.environ['PATH'])

    @classmethod
    def tearDownClass(cls):
        AbstractTestWithRepo.tearDownClass()
        os.environ['PATH'] = LeafCliWrapper.OLD_PATH

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.leafExec("config", "--root", self.getInstallFolder())
        self.leafExec(("remote", "add"), "--insecure",
                      "default", self.getRemoteUrl())
        self.leafExec(("remote", "add"), "--insecure",
                      "other", self.getRemoteUrl2())

    def leafExec(self, verb, *args, altWorkspace=None, expectedRc=0):
        if altWorkspace is None:
            altWorkspace = self.getWorkspaceFolder()
        self.eazyExecute(self.preVerbArgs + ["--non-interactive",
                                             "--workspace", altWorkspace],
                         verb,
                         self.postVerbArgs,
                         args,
                         expectedRc)

    def eazyExecute(self, preArgs, verb, postArgs, args, expectedRc):
        command = []
        if preArgs is not None:
            command += preArgs
        if verb is not None:
            if isinstance(verb, (list, tuple)):
                command += verb
            else:
                command.append(verb)
        if postArgs is not None:
            command += postArgs
        if args is not None:
            command += args
        command = [str(i) for i in command]
        out = LeafCli().run(command)
        if expectedRc is not None:
            self.assertEqual(expectedRc, out, " ".join(command))
        return out


def generateRepo(sourceFolder, outputFolder):
    if not outputFolder.is_dir():
        outputFolder.mkdir(parents=True)
    artifactsList = []
    artifactsList2 = []

    rm = RelengManager(Verbosity.QUIET, True)
    for packageFolder in sourceFolder.iterdir():
        if packageFolder.is_dir():
            manifestFile = packageFolder / LeafFiles.MANIFEST
            if manifestFile.is_file():
                manifest = Manifest.parse(manifestFile)
                if str(manifest.getIdentifier()) != packageFolder.name:
                    raise ValueError("Naming error: %s != %s" % (
                        str(manifest.getIdentifier()), packageFolder.name))
                filename = str(manifest.getIdentifier()) + ".leaf"
                outputFile = outputFolder / filename
                rm.createPackage(
                    packageFolder,
                    outputFile,
                    compression=ALT_COMPRESSION.get(str(manifest.getIdentifier())))
                # Check that the generated archive is OK
                checkArchiveFormat(
                    outputFile,
                    ALT_COMPRESSION.get(str(manifest.getIdentifier())))
                # Create multi index.json
                if manifest.getName() == "install":
                    artifactsList2.append(outputFile)
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

    rm.generateIndex(outputFolder / "index.json",
                     artifactsList,
                     name="First repository",
                     description="First repository description")
    rm.generateIndex(outputFolder / "index2.json",
                     artifactsList2,
                     name="Second repository",
                     description="Second repository description")

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
    if compression == "xz":
        checkMime(file, "x-xz")
    elif compression == "tar":
        checkMime(file, "x-tar")
    elif compression == "gz":
        checkMime(file, "gzip")
    elif compression == "bz2":
        checkMime(file, "x-bzip2")
    else:
        checkMime(file, "x-xz")


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
