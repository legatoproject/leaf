'''
@author: seb
'''

from leaf.constants import LeafConstants
from leaf.core import LeafApp
from leaf.logger import createLogger
from leaf.model import PackageIdentifier
from leaf.utils import isFolderIgnored
import time
import unittest

from tests.utils import TestWithRepository


VERBOSE = True


class TestPackageManager_File(TestWithRepository):

    def __init__(self, methodName):
        TestWithRepository.__init__(self, methodName)
        self.logger = createLogger(VERBOSE, False, False)

    def setUp(self):
        TestWithRepository.setUp(self)

        self.app = LeafApp(self.logger,
                           TestWithRepository.CONFIG_FILE,
                           TestWithRepository.CACHE_FILE)
        self.app.updateConfiguration(self.getInstallFolder())
        self.assertEqual(0, len(self.app.listAvailablePackages()))
        self.assertEqual(0, len(self.app.listInstalledPackages()))
        self.assertEqual(0, len(self.app.getRemoteUrls()))
        self.assertEqual(0, len(self.app.getRemoteRepositories()))
        self.app.remoteAdd(self.getRemoteUrl())
        self.assertEqual(1, len(self.app.getRemoteUrls()))
        self.assertEqual(1, len(self.app.getRemoteRepositories()))
        self.app.fetchRemotes()

    def checkContent(self, content, pisList):
        self.assertEqual(len(content), len(pisList))
        for pis in pisList:
            self.assertTrue(PackageIdentifier.fromString(pis) in content)

    def testCompression(self):
        packs = ["compress-bz2_1.0", "compress-gz_1.0",
                 "compress-tar_1.0", "compress-xz_1.0"]
        self.app.installPackages(packs)
        self.checkContent(self.app.listInstalledPackages(), packs)

    def testComposite(self):
        packs = ["composite_1.0"]
        self.app.installPackages(packs)
        self.checkContent(self.app.listInstalledPackages(), packs)

    def testContainer(self):
        self.app.installPackages(["container-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0"])

        self.app.installPackages(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0",
                          "container-A_2.0", "container-D_1.0"])

        self.app.uninstallPackages(["container-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.0", "container-C_1.0", "container-D_1.0"])

        self.app.uninstallPackages(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testBadContainer(self):
        with self.assertRaises(Exception):
            self.app.installPackages(["failure-depends-leaf_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testContainerNotMaster(self):
        self.app.installPackages(["container-A_1.1"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0"])

        self.app.installPackages(["container-A_2.1"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0",
                          "container-A_2.1", "container-D_1.0"])

        self.app.uninstallPackages(["container-A_1.1"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.1", "container-C_1.0", "container-D_1.0"])

        self.app.uninstallPackages(["container-A_2.1"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testDebDepends(self):
        self.app.installPackages(["deb_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["deb_1.0"])

        with self.assertRaises(Exception):
            self.app.installPackages(["failure-depends-deb_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["deb_1.0"])

        self.app.installPackages(["failure-depends-deb_1.0"],
                                 bypassAptDependsCheck=True)
        self.checkContent(self.app.listInstalledPackages(), [
                          "deb_1.0", "failure-depends-deb_1.0"])

    def testSteps(self):
        self.app.installPackages(["install_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["install_1.0"])

        folder = self.getInstallFolder() / "install_1.0"

        self.assertTrue(folder.is_dir())
        self.assertTrue((folder / "data1").is_file())
        self.assertTrue((folder / "folder").is_dir())
        self.assertFalse((folder / "folder" / "data2").is_file())
        self.assertTrue((folder / "folder" / "data1-symlink").is_symlink())

        self.assertFalse((self.getInstallFolder() / "uninstall.log").is_file())
        self.assertTrue((folder / "postinstall.log").is_file())
        self.assertTrue((folder / "targetFileFromEnv").is_file())
        self.assertTrue((folder / "downloadedFile").is_file())
        self.assertTrue((folder / "folder2").is_dir())
        self.assertTrue((folder / "folder2" / "data2-symlink").is_symlink())
        self.assertTrue((folder / "data2-copy").is_file())
        with open(str(folder / "targetFileFromEnv"), 'r') as fp:
            content = fp.readlines()
            self.assertEqual(1, len(content))
            # FIXME \n at the end?
            self.assertEqual(str(folder) + "\n", content[0])

        self.app.uninstallPackages(["install_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])
        self.assertTrue((self.getInstallFolder() / "uninstall.log").is_file())

    def testPostinstallError(self):
        with self.assertRaises(Exception):
            self.app.installPackages(["failure-postinstall-exec_1.0"],
                                     keepFolderOnError=True)
        found = False
        for folder in self.getInstallFolder().iterdir():
            if folder.name.startswith("failure-postinstall-exec_1.0"):
                self.assertTrue(isFolderIgnored(folder))
                found = True
                break
        self.assertTrue(found)

    def testInstallLatest(self):
        self.app.installPackages(["version"])
        self.checkContent(self.app.listInstalledPackages(), ["version_2.0"])

    def testCannotUninstallToKeepDependencies(self):
        self.app.installPackages(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.0", "container-C_1.0", "container-D_1.0"])

        self.app.uninstallPackages(["container-C_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [
                          "container-A_2.0", "container-C_1.0", "container-D_1.0"])

    def testEnv(self):
        self.app.installPackages(["env-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["env-A_1.0", "env-B_1.0"])

        env = self.app.getEnv(["env-A_1.0"])
        self.assertEqual(4, len(env))
        self.assertEqual([
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            env)

    def testSilentFail(self):
        with self.assertRaises(Exception):
            self.app.installPackages(["failure-postinstall-download_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

        with self.assertRaises(Exception):
            self.app.installPackages(["failure-postinstall-exec_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

        self.app.installPackages(["failure-postinstall-download-silent_1.0",
                                  "failure-postinstall-exec-silent_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["failure-postinstall-download-silent_1.0",
                                                             "failure-postinstall-exec-silent_1.0"])

    def testDownloadTimeout(self):
        start = time.time()
        with self.assertRaises(Exception):
            self.app.installPackages(["failure-postinstall-download_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])
        duration = time.time() - start
        self.assertTrue(duration > LeafConstants.DOWNLOAD_TIMEOUT,
                        msg="Duration: " + str(duration))
        self.assertTrue(duration < (LeafConstants.DOWNLOAD_TIMEOUT + 2),
                        msg="Duration: " + str(duration))

    def testDepends(self):
        self.assertEqual(["python3"],
                         self.app.listDependencies(["deb_1.0"],
                                                   aptDepends=True))
        self.assertEqual(["python42"],
                         self.app.listDependencies(["failure-depends-deb_1.0"],
                                                   aptDepends=True))
        self.assertEqual(["python3", "python42"],
                         self.app.listDependencies(["deb_1.0", "failure-depends-deb_1.0"],
                                                   aptDepends=True))
        self.assertEqual(["python42"],
                         self.app.listDependencies(["deb_1.0", "failure-depends-deb_1.0"],
                                                   aptDepends=True, filterInstalled=True))

    def testResolveLastVersion(self):
        self.app.installPackages(["container-A_2.0"])
        self.assertEqual([PackageIdentifier.fromString("container-A_2.0")],
                         self.app.resolveLatest(["container-A"],
                                                ipMap=True))
        self.assertEqual([PackageIdentifier.fromString("container-A_2.1")],
                         self.app.resolveLatest(["container-A"],
                                                apMap=True))
        with self.assertRaises(Exception):
            self.app.resolveLatest(["container-A"])


if __name__ == "__main__":
    unittest.main()
