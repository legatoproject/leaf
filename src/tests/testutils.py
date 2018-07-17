from _io import StringIO
import os
import shutil
import sys
from tempfile import mkdtemp

from pathlib import Path

from contextlib import contextmanager
from leaf.cli.cli import LeafCli
from leaf.constants import EnvConstants, LeafFiles
from leaf.core.relengmanager import RelengManager
from leaf.format.logger import TextLogger, Verbosity
from leaf.model.package import PackageIdentifier, Manifest
import subprocess
import unittest
from unittest.case import TestCase


LEAF_UT_DEBUG = os.environ.get("LEAF_UT_DEBUG")
LEAF_UT_SKIP = os.environ.get("LEAF_UT_SKIP", "")

ROOT_FOLDER = Path(__file__).parent / '..' / '..'
RESOURCE_FOLDER = ROOT_FOLDER / "src" / "tests" / "resources"
EXPECTED_OUTPUT_FOLDER = ROOT_FOLDER / "src" / "tests" / "expected_ouput"
EXTENSIONS_FOLDER = ROOT_FOLDER / "resources" / "bin"

SEPARATOR = "--------------------"
ALT_FILENAMES = {
    "compress-tar_1.0": 'compress-tar_1.0.tar',
    "compress-xz_1.0":  'compress-xz_1.0.tar.xz',
    "compress-bz2_1.0": 'compress-bz2_1.0.tar.bz2',
    "compress-gz_1.0":  'compress-gz_1.0.tar.gz'
}


class StringIOWrapper(StringIO):

    def __init__(self, stream, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.__altstream__ = stream

    def write(self, txt):
        super().write(txt)
        self.__altstream__.write(txt)


class ContentChecker():
    _STDOUT = sys.stdout
    _STDERR = sys.stderr

    def __init__(self, tester, stdoutFile=None, stderrFile=None, variables=None):
        self.tester = tester
        self.stdoutFile, self.stderrFile = stdoutFile, stderrFile
        self.variables = variables
        self.stdout = StringIOWrapper(ContentChecker._STDOUT)
        self.stderr = StringIOWrapper(ContentChecker._STDERR)

    def __enter__(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def __exit__(self, *args):
        sys.stdout = ContentChecker._STDOUT
        sys.stderr = ContentChecker._STDERR
        self._checkContent(self.stdoutFile, self.stdout)
        self._checkContent(self.stderrFile, self.stderr)

    def _checkContent(self, file, stream):
        lines = []
        streamLines = stream.getvalue().splitlines()
        if file is not None:
            with open(str(file)) as fp:
                for line in fp.read().splitlines():
                    if self.variables is not None:
                        for k, v in self.variables.items():
                            line = line.replace(k, v)
                    lines.append(line)
        self.tester.assertEqual(
            lines,
            streamLines)


class AbstractTestWithRepo(unittest.TestCase):

    ROOT_FOLDER = None
    REPO_FOLDER = None
    VOLATILE_FOLDER = None

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

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
                     AbstractTestWithRepo.REPO_FOLDER,
                     TextLogger(Verbosity.QUIET, nonInteractive=True))

    @classmethod
    def tearDownClass(cls):
        if LEAF_UT_DEBUG is None:
            shutil.rmtree(str(AbstractTestWithRepo.ROOT_FOLDER), True)

    def assertStdout(self, stdout=None, stderr=None, variables=None):
        classFolder = EXPECTED_OUTPUT_FOLDER / self.__class__.__name__
        self.assertTrue(classFolder.is_dir())
        stdoutFile, stderrFile = None, None
        if stdout is not None:
            stdoutFile = classFolder / stdout
        if stderr is not None:
            stderrFile = classFolder / stderr
        return ContentChecker(self,
                              stdoutFile=stdoutFile,
                              stderrFile=stderrFile,
                              variables=variables)

    def setUp(self):
        shutil.rmtree(str(AbstractTestWithRepo.VOLATILE_FOLDER),
                      ignore_errors=True)
        AbstractTestWithRepo.VOLATILE_FOLDER.mkdir()
        os.environ[EnvConstants.CUSTOM_CONFIG_FILE] = str(
            self.getConfigurationFile())
        os.environ[EnvConstants.CUSTOM_CACHE_FOLDER] = str(
            self.getCacheFolder())

    def tearDown(self):
        pass

    def getRemoteUrl(self):
        return (AbstractTestWithRepo.REPO_FOLDER / "index.json").as_uri()

    def getCompositeUrl(self):
        return (AbstractTestWithRepo.REPO_FOLDER / "composite.json").as_uri()

    def getVolatileItem(self, name, mkdir=True):
        out = AbstractTestWithRepo.VOLATILE_FOLDER / name
        if mkdir and not out.is_dir():
            out.mkdir()
        return out

    def getConfigurationFile(self):
        return self.getVolatileItem("config.json", mkdir=False)

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
        self.leafExec(("remote", "add"), "default", self.getRemoteUrl())

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


def generateRepo(sourceFolder, outputFolder, logger):
    if not outputFolder.is_dir():
        outputFolder.mkdir(parents=True)
    artifactsList = []
    artifactsListComposite = []

    app = RelengManager(logger)
    for packageFolder in sourceFolder.iterdir():
        if packageFolder.is_dir():
            manifestFile = packageFolder / LeafFiles.MANIFEST
            if manifestFile.is_file():
                manifest = Manifest.parse(manifestFile)
                if str(manifest.getIdentifier()) != packageFolder.name:
                    raise ValueError("Naming error: %s != %s" % (
                        str(manifest.getIdentifier()), packageFolder.name))
                filename = ALT_FILENAMES.get(str(manifest.getIdentifier()),
                                             str(manifest.getIdentifier()) + ".leaf")
                outputFile = outputFolder / filename
                app.pack(manifestFile, outputFile, updateDate=False)
                checkArchiveFormat(str(outputFile))
                if manifest.getName().startswith("composite"):
                    artifactsListComposite.append(outputFile)
                else:
                    artifactsList.append(outputFile)

    app.index(outputFolder / "composite.json",
              artifactsListComposite, "composite")

    app.index(outputFolder / "index.json",
              artifactsList, "composite", composites=["composite.json"])


def checkArchiveFormat(file):
    if (file.endswith(".tar")):
        checkMime(file, "x-tar")
    elif (file.endswith(".tar.gz")):
        checkMime(file, "gzip")
    elif (file.endswith(".tar.bz2")):
        checkMime(file, "x-bzip2")
    elif (file.endswith(".tar.xz")):
        checkMime(file, "x-xz")
    else:
        checkMime(file, "x-xz")


def checkMime(file, expectedMime):
    mime = subprocess.getoutput("file -bi " + str(file))
    if not mime.startswith("application/" + expectedMime):
        raise ValueError("File %s has invalid mime type %s" % (file, mime))


def envFileToMap(envDumpFile):
    out = {}
    with open(str(envDumpFile), "r") as fp:
        for line in fp.read().splitlines():
            i = line.index("=")
            out[line[:i]] = line[i + 1:]
    return out
