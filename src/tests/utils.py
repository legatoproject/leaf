
'''
Constants to tweak the tests
'''
from leaf.cli import LeafCli
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import LeafRepository
from leaf.logger import TextLogger
from leaf.model import Manifest, PackageIdentifier
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import mkdtemp
import unittest
from unittest.case import TestCase


LEAF_UT_DEBUG = os.environ.get("LEAF_UT_DEBUG")
RESOURCE_FOLDER = Path("tests/resources/")

SEPARATOR = "--------------------"
ALT_FILENAMES = {
    "compress-tar_1.0": 'compress-tar_1.0.tar',
    "compress-xz_1.0":  'compress-xz_1.0.tar.xz',
    "compress-bz2_1.0": 'compress-bz2_1.0.tar.bz2',
    "compress-gz_1.0":  'compress-gz_1.0.tar.gz'
}


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
                     TextLogger(TextLogger.LEVEL_QUIET))

    @classmethod
    def tearDownClass(cls):
        if not LEAF_UT_DEBUG is not None:
            shutil.rmtree(str(AbstractTestWithRepo.ROOT_FOLDER), True)

    def setUp(self):
        shutil.rmtree(str(AbstractTestWithRepo.VOLATILE_FOLDER),
                      ignore_errors=True)
        AbstractTestWithRepo.VOLATILE_FOLDER.mkdir()
        os.environ[LeafConstants.ENV_CONFIG_FILE] = str(
            self.getConfigurationFile())
        os.environ[LeafConstants.ENV_CACHE_FOLDER] = str(
            self.getCacheFolder())

    def tearDown(self):
        pass

    def getRemoteUrl(self):
        return (AbstractTestWithRepo.REPO_FOLDER / "index.json").as_uri()

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
        self.jsonEnvValue = ""

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.leafExec("config:user",
                      "--root", self.getInstallFolder())
        self.leafExec("config:user",
                      "--add-remote", self.getRemoteUrl())

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
            if isinstance(verb, list):
                command += verb
            else:
                command.append(verb)
        if postArgs is not None:
            command += postArgs
        if args is not None:
            command += args
        command = [str(i) for i in command]
        print(SEPARATOR,
              '[%s] leaf %s' % (type(self).__name__,
                                " ".join(command)))
        os.environ[LeafConstants.ENV_JSON_OUTPUT] = self.jsonEnvValue
        out = LeafCli().run(command)
        print(SEPARATOR + SEPARATOR + SEPARATOR)
        if expectedRc is not None:
            self.assertEqual(expectedRc, out, " ".join(command))
        return out


def generateRepo(sourceFolder, outputFolder, logger):
    if not outputFolder.is_dir():
        outputFolder.mkdir(parents=True)
    artifactsList = []
    artifactsListComposite = []

    app = LeafRepository(logger)
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


def envFileToMap(envDumpFile):
    out = {}
    with open(str(envDumpFile), "r") as fp:
        for line in fp.read().splitlines():
            i = line.index("=")
            out[line[:i]] = line[i + 1:]
    return out
