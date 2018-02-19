'''
Created on 23 nov. 2017

@author: seb
'''
'''
Constants to tweak the tests
'''

from leaf.core import LeafConstants, LeafApp, PackageIdentifier,\
    JsonConstants, LeafUtils, VerboseLogger, QuietLogger
from pathlib import Path
import shutil
from tempfile import mkdtemp
import time
import unittest
from unittest.case import TestCase

from tests.releng import RepositoryUtils


_VERBOSE = False


class LeafAppTest():

    REPO_FOLDER = None
    INSTALL_FOLDER = None
    CACHE_FOLDER = None
    LOGGER = VerboseLogger() if _VERBOSE else QuietLogger()

    @classmethod
    def setUpClass(cls):
        LeafAppTest.ROOT_FOLDER = Path(mkdtemp(prefix="leaf_tests_"))
        #LeafAppTest.ROOT_FOLDER = Path("/tmp/leaf")
        LeafAppTest.REPO_FOLDER = LeafAppTest.ROOT_FOLDER / "repo"
        LeafAppTest.INSTALL_FOLDER = LeafAppTest.ROOT_FOLDER / "app"
        LeafAppTest.CACHE_FOLDER = LeafConstants.CACHE_FOLDER

        shutil.rmtree(str(LeafAppTest.ROOT_FOLDER), True)

        RepositoryUtils.generateRepo(
            Path("tests/resources/"), LeafAppTest.REPO_FOLDER, LeafAppTest.LOGGER)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(LeafAppTest.ROOT_FOLDER), True)

    def __init__(self, url):
        self.url = str(url)
        print("Using repo url: " + self.url)

    def getRemoteUrl(self):
        pass

    def setUp(self):
        shutil.rmtree(str(LeafAppTest.INSTALL_FOLDER), ignore_errors=True)
        shutil.rmtree(str(LeafAppTest.CACHE_FOLDER), ignore_errors=True)
        LeafAppTest.INSTALL_FOLDER.mkdir(parents=True)

        self.app = LeafApp(
            LeafAppTest.LOGGER, LeafAppTest.INSTALL_FOLDER / "config.json")
        self.app.writeConfiguration(
            {JsonConstants.CONFIG_ROOT: str(LeafAppTest.INSTALL_FOLDER)})
        self.assertEqual(0, len(self.app.listAvailablePackages()))
        self.assertEqual(0, len(self.app.listInstalledPackages()))
        self.assertEqual(0, len(self.app.remoteList()))
        self.app.remoteAdd(self.getRemoteUrl())
        self.assertEqual(1, len(self.app.remoteList()))
        self.app.fetchRemotes()

    def tearDown(self):
        shutil.rmtree(str(LeafAppTest.INSTALL_FOLDER), True)

    def checkContent(self, content, pisList):
        self.assertEqual(len(content), len(pisList))
        for pis in pisList:
            self.assertTrue(PackageIdentifier.fromString(pis) in content)

    def testCompression(self):
        packs = ["compress-bz2_1.0", "compress-gz_1.0",
                 "compress-tar_1.0", "compress-xz_1.0"]
        self.app.install(packs)
        self.checkContent(self.app.listInstalledPackages(), packs)

    def testComposite(self):
        packs = ["composite_1.0"]
        self.app.install(packs)
        self.checkContent(self.app.listInstalledPackages(), packs)

    def testContainer(self):
        self.app.install(["container-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0"])

        self.app.install(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0",
                          "container-A_2.0", "container-D_1.0"])

        self.app.uninstall(["container-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.0", "container-C_1.0", "container-D_1.0"])

        self.app.uninstall(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testBadContainer(self):
        with self.assertRaises(Exception):
            self.app.install(["failure-depends-leaf_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testContainerNotMaster(self):
        self.app.install(["container-A_1.1"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0"])

        self.app.install(["container-A_2.1"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0",
                          "container-A_2.1", "container-D_1.0"])

        self.app.uninstall(["container-A_1.1"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.1", "container-C_1.0", "container-D_1.0"])

        self.app.uninstall(["container-A_2.1"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testDebDepends(self):
        self.app.install(["deb_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["deb_1.0"])

        with self.assertRaises(Exception):
            self.app.install(["failure-depends-deb_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["deb_1.0"])

        self.app.install(["failure-depends-deb_1.0"], forceInstall=True)
        self.checkContent(self.app.listInstalledPackages(), [
                          "deb_1.0", "failure-depends-deb_1.0"])

    def testSteps(self):
        self.app.install(["install_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["install_1.0"])

        folder = LeafAppTest.INSTALL_FOLDER / "install_1.0"

        self.assertTrue(folder.is_dir())
        self.assertTrue((folder / "data1").is_file())
        self.assertTrue((folder / "folder").is_dir())
        self.assertFalse((folder / "folder" / "data2").is_file())
        self.assertTrue((folder / "folder" / "data1-symlink").is_symlink())

        self.assertFalse(
            (LeafAppTest.INSTALL_FOLDER / "uninstall.log").is_file())
        self.assertTrue((folder / "postinstall.log").is_file())
        self.assertTrue((folder / "targetFileFromEnv").is_file())
        self.assertTrue((folder / "downloadedFile").is_file())
        self.assertTrue((folder / "folder2").is_dir())
        self.assertTrue((folder / "folder2" / "data2-symlink").is_symlink())
        self.assertTrue((folder / "data2-copy").is_file())
        with open(str(folder / "targetFileFromEnv"), 'r') as fp:
            content = fp.readlines()
            self.assertEquals(1, len(content))
            # FIXME \n at the end?
            self.assertEquals(str(folder) + "\n", content[0])

        self.app.uninstall(["install_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])
        self.assertTrue(
            (LeafAppTest.INSTALL_FOLDER / "uninstall.log").is_file())

    def testPostinstallError(self):
        with self.assertRaises(Exception):
            self.app.install(["failure-postinstall-exec_1.0"],
                             keepFolderOnError=True)
        found = False
        for folder in LeafAppTest.INSTALL_FOLDER.iterdir():
            if folder.name.startswith("failure-postinstall-exec_1.0"):
                self.assertTrue(LeafUtils.isFolderIgnored(folder))
                found = True
                break
        self.assertTrue(found)

    def testInstallLatest(self):
        self.app.install(["version"])
        self.checkContent(self.app.listInstalledPackages(), ["version_2.0"])

    def testCannotUninstallToKeepDependencies(self):
        self.app.install(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.0", "container-C_1.0", "container-D_1.0"])

        self.app.uninstall(["container-C_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.0", "container-C_1.0", "container-D_1.0"])

    def testEnv(self):
        self.app.install(["env-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["env-A_1.0", "env-B_1.0"])

        env = self.app.getEnv(["env-A_1.0"])
        self.assertEquals(4, len(env))
        value = "$PATH:%s:%s" % (str(LeafAppTest.INSTALL_FOLDER /
                                     "env-A_1.0"),
                                 str(LeafAppTest.INSTALL_FOLDER /
                                     "env-B_1.0"))
        self.assertEquals(value, env["LEAF_PATH_A"])
        self.assertEquals("FOO", env["LEAF_ENV_A"])
        self.assertEquals("BAR", env["LEAF_ENV_B"])

    def testSilentFail(self):
        with self.assertRaises(Exception):
            self.app.install(["failure-postinstall-download_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

        with self.assertRaises(Exception):
            self.app.install(["failure-postinstall-exec_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

        self.app.install(["failure-postinstall-download-silent_1.0",
                          "failure-postinstall-exec-silent_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["failure-postinstall-download-silent_1.0",
                                                             "failure-postinstall-exec-silent_1.0"])

    def testDownloadTimeout(self):
        start = time.time()
        with self.assertRaises(Exception):
            self.app.install(["failure-postinstall-download_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])
        duration = time.time() - start
        self.assertTrue(duration > LeafConstants.DOWNLOAD_TIMEOUT,
                        msg="Duration: " + str(duration))
        self.assertTrue(duration < (LeafConstants.DOWNLOAD_TIMEOUT + 2),
                        msg="Duration: " + str(duration))


class FileLeafTest(LeafAppTest, unittest.TestCase):

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    def getRemoteUrl(self):
        return (LeafAppTest.REPO_FOLDER / "index.json").as_uri()


if __name__ == "__main__":
    unittest.main()
