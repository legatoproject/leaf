
'''
Constants to tweak the tests
'''
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import LeafRepository
from leaf.logger import TextLogger
from leaf.model import Manifest
from pathlib import Path
import shutil
import subprocess
from tempfile import mkdtemp
import unittest
from unittest.case import TestCase


_DEBUG_TESTS = False


class TestWithRepository(unittest.TestCase):

    ALT_FILENAMES = {
        "compress-tar_1.0": 'compress-tar_1.0.tar',
        "compress-xz_1.0":  'compress-xz_1.0.tar.xz',
        "compress-bz2_1.0": 'compress-bz2_1.0.tar.bz2',
        "compress-gz_1.0":  'compress-gz_1.0.tar.gz'
    }

    ROOT_FOLDER = None
    REPO_FOLDER = None
    INSTALL_FOLDER = None
    CACHE_FOLDER = LeafFiles.CACHE_FOLDER

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        if _DEBUG_TESTS:
            TestWithRepository.ROOT_FOLDER = Path("/tmp/leaf")
        else:
            TestWithRepository.ROOT_FOLDER = Path(
                mkdtemp(prefix="leaf_tests_"))

        TestWithRepository.REPO_FOLDER = TestWithRepository.ROOT_FOLDER / "repo"
        TestWithRepository.INSTALL_FOLDER = TestWithRepository.ROOT_FOLDER / "app"

        shutil.rmtree(str(TestWithRepository.ROOT_FOLDER), True)

        TestWithRepository.generateRepo(Path("tests/resources/"),
                                        TestWithRepository.REPO_FOLDER,
                                        TextLogger(TextLogger.LEVEL_QUIET))

    @classmethod
    def tearDownClass(cls):
        if not _DEBUG_TESTS:
            shutil.rmtree(str(TestWithRepository.ROOT_FOLDER), True)

    def setUp(self):
        shutil.rmtree(str(TestWithRepository.INSTALL_FOLDER),
                      ignore_errors=True)
        shutil.rmtree(str(TestWithRepository.CACHE_FOLDER),
                      ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(str(TestWithRepository.INSTALL_FOLDER),
                      ignore_errors=True)
        shutil.rmtree(str(TestWithRepository.CACHE_FOLDER),
                      ignore_errors=True)

    def getRemoteUrl(self):
        return (TestWithRepository.REPO_FOLDER / "index.json").as_uri()

    def getInstallFolder(self):
        return TestWithRepository.INSTALL_FOLDER

    @staticmethod
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
                        raise ValueError(
                            "Naming error: " + str(manifest.getIdentifier()) + " != " + packageFolder.name)
                    filename = TestWithRepository.ALT_FILENAMES.get(str(manifest.getIdentifier()),
                                                                    str(manifest.getIdentifier()) + ".leaf")
                    outputFile = outputFolder / filename
                    app.pack(manifestFile, outputFile)
                    TestWithRepository.checkArchiveFormat(str(outputFile))
                    if manifest.getName().startswith("composite"):
                        artifactsListComposite.append(outputFile)
                    else:
                        artifactsList.append(outputFile)

        app.index(outputFolder / "composite.json",
                  artifactsListComposite, "composite")

        app.index(outputFolder / "index.json",
                  artifactsList, "composite", composites=["composite.json"])

    @staticmethod
    def checkArchiveFormat(file):
        if (file.endswith(".tar")):
            TestWithRepository.checkMime(file, "x-tar")
        elif (file.endswith(".tar.gz")):
            TestWithRepository.checkMime(file, "gzip")
        elif (file.endswith(".tar.bz2")):
            TestWithRepository.checkMime(file, "x-bzip2")
        elif (file.endswith(".tar.xz")):
            TestWithRepository.checkMime(file, "x-xz")
        else:
            TestWithRepository.checkMime(file, "x-xz")

    @staticmethod
    def checkMime(file, expectedMime):
        mime = subprocess.getoutput("file -bi " + str(file))
        if not mime.startswith("application/" + expectedMime):
            raise ValueError("Invalid mime: " + file + ": " + mime)
