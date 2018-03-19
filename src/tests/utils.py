
'''
Constants to tweak the tests
'''
from leaf.cli import LeafCli
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import LeafRepository
from leaf.logger import TextLogger
from leaf.model import Manifest
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import mkdtemp
import unittest
from unittest.case import TestCase


DEBUG_TESTS = os.environ.get("LEAF_UT_KEEP")

ALT_FILENAMES = {
    "compress-tar_1.0": 'compress-tar_1.0.tar',
    "compress-xz_1.0":  'compress-xz_1.0.tar.xz',
    "compress-bz2_1.0": 'compress-bz2_1.0.tar.bz2',
    "compress-gz_1.0":  'compress-gz_1.0.tar.gz'
}


class TestWithRepository(unittest.TestCase):

    ROOT_FOLDER = None
    REPO_FOLDER = None
    VOLATILE_FOLDER = None
    INSTALL_FOLDER = None
    WS_FOLDER = None
    CONFIG_FILE = None
    CACHE_FILE = None
    CACHE_FOLDER = LeafFiles.CACHE_FOLDER

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        if DEBUG_TESTS is not None:
            TestWithRepository.ROOT_FOLDER = Path("/tmp/leaf")
        else:
            TestWithRepository.ROOT_FOLDER = Path(
                mkdtemp(prefix="leaf_tests_"))

        TestWithRepository.REPO_FOLDER = TestWithRepository.ROOT_FOLDER / "repository"
        TestWithRepository.VOLATILE_FOLDER = TestWithRepository.ROOT_FOLDER / "volatile"
        TestWithRepository.INSTALL_FOLDER = TestWithRepository.VOLATILE_FOLDER / "packages"
        TestWithRepository.WS_FOLDER = TestWithRepository.VOLATILE_FOLDER / "workspace"
        TestWithRepository.CONFIG_FILE = TestWithRepository.VOLATILE_FOLDER / "leaf-config.json"
        TestWithRepository.CACHE_FILE = TestWithRepository.VOLATILE_FOLDER / "remote-cache.json"

        shutil.rmtree(str(TestWithRepository.ROOT_FOLDER), ignore_errors=True)

        resourcesFolder = Path("tests/resources/")
        assert resourcesFolder.exists(), "Cannot find resources folder!"
        generateRepo(resourcesFolder,
                     TestWithRepository.REPO_FOLDER,
                     TextLogger(TextLogger.LEVEL_QUIET))

    @classmethod
    def tearDownClass(cls):
        if not DEBUG_TESTS is not None:
            shutil.rmtree(str(TestWithRepository.ROOT_FOLDER), True)

    def setUp(self):
        shutil.rmtree(str(TestWithRepository.VOLATILE_FOLDER),
                      ignore_errors=True)
        TestWithRepository.VOLATILE_FOLDER.mkdir()
        TestWithRepository.WS_FOLDER.mkdir()
        TestWithRepository.INSTALL_FOLDER.mkdir()

    def tearDown(self):
        pass

    def getRemoteUrl(self):
        return (TestWithRepository.REPO_FOLDER / "index.json").as_uri()

    def getInstallFolder(self):
        return TestWithRepository.INSTALL_FOLDER

    def getWorkspaceFolder(self):
        return TestWithRepository.WS_FOLDER


class LeafCliWrapper():

    SEPARATOR = "--------------------"

    def __init__(self):
        self.preCommandArgs = []
        self.postCommandArgs = []

    def initLeafConfig(self, configurationFile, setRoot=True, addRemote=True):
        self.preCommandArgs += ["--config", configurationFile]
        self.leafExec("config", "--root", self.getInstallFolder())
        self.leafExec("remote", "--add", self.getRemoteUrl())

    def leafExec(self, verb, *args, checkRc=True):
        command = []
        command += self.preCommandArgs
        if isinstance(verb, (list, tuple)):
            command += verb
        else:
            command.append(verb)
        command += self.postCommandArgs
        command += args
        command = [str(i) for i in command]
        print(LeafCliWrapper.SEPARATOR,
              "[" + type(self).__name__ + "]",
              "Execute:",
              " ".join(command))
        out = LeafCli().execute(command)
        print(LeafCliWrapper.SEPARATOR +
              LeafCliWrapper.SEPARATOR +
              LeafCliWrapper.SEPARATOR)
        if checkRc:
            self.assertEqual(0, out, " ".join(command))
        return out


def generateRepo(sourceFolder, outputFolder, logger):
    outputFolder.mkdir(parents=True, exist_ok=True)
    artifactsList = []
    artifactsListComposite = []

    app = LeafRepository(logger)
    for packageFolder in sourceFolder.iterdir():
        if packageFolder.is_dir():
            manifestFile = packageFolder / LeafConstants.MANIFEST
            if manifestFile.is_file():
                manifest = Manifest.parse(manifestFile)
                if str(manifest.getIdentifier()) != packageFolder.name:
                    raise ValueError("Naming error: %s != %s" % (
                        str(manifest.getIdentifier()), packageFolder.name))
                filename = ALT_FILENAMES.get(str(manifest.getIdentifier()),
                                             str(manifest.getIdentifier()) + ".leaf")
                outputFile = outputFolder / filename
                app.pack(manifestFile, outputFile)
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
