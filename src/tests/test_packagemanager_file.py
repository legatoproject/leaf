'''
@author: seb
'''

from datetime import datetime, timedelta
import os
import platform
import sys
import time
import unittest

from leaf.constants import LeafConstants
from leaf.core.dependencies import DependencyType
from leaf.core.logger import Verbosity, TextLogger
from leaf.core.packagemanager import PackageManager
from leaf.model.base import Environment
from leaf.model.package import PackageIdentifier, AvailablePackage,\
    InstalledPackage
from leaf.utils import isFolderIgnored
from tests.testutils import AbstractTestWithRepo, envFileToMap


VERBOSITY = Verbosity.VERBOSE


class TestPackageManager_File(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)

        os.environ[LeafConstants.ENV_CONFIG_FILE] = str(
            self.getConfigurationFile())
        os.environ[LeafConstants.ENV_CACHE_FOLDER] = str(
            self.getCacheFolder())
        self.app = PackageManager(TextLogger(VERBOSITY, True),
                                  nonInteractive=True)

        if "LEAF_TIMEOUT" not in os.environ:
            # Fix CI timeout
            os.environ["LEAF_TIMEOUT"] = "30"
            print("Override LEAF_TIMEOUT=" + os.environ["LEAF_TIMEOUT"],
                  file=sys.stderr)

        self.app.updateUserConfiguration(rootFolder=self.getInstallFolder())
        self.assertEqual(0, len(self.app.listAvailablePackages()))
        self.assertEqual(0, len(self.app.listInstalledPackages()))
        self.assertEqual(0, len(self.app.readConfiguration().getRemotes()))
        self.assertEqual(0, len(self.app.getRemoteRepositories()))
        self.app.updateUserConfiguration(remoteAddList=[self.getRemoteUrl()])
        self.assertEqual(1, len(self.app.readConfiguration().getRemotes()))
        self.app.fetchRemotes(True)
        self.assertEqual(2, len(self.app.getRemoteRepositories()))

    def testCompression(self):
        packs = ["compress-bz2_1.0",
                 "compress-gz_1.0",
                 "compress-tar_1.0",
                 "compress-xz_1.0"]
        self.app.installFromRemotes(packs)
        self.checkContent(self.app.listInstalledPackages(), packs)

    def testComposite(self):
        packs = ["composite_1.0"]
        self.app.installFromRemotes(packs)
        self.checkContent(self.app.listInstalledPackages(), packs)

    def testContainer(self):
        self.app.installFromRemotes(["container-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_1.0",
                                                             "container-B_1.0",
                                                             "container-C_1.0",
                                                             "container-E_1.0"])

        self.app.installFromRemotes(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_1.0",
                                                             "container-B_1.0",
                                                             "container-C_1.0",
                                                             "container-E_1.0",
                                                             "container-A_2.0",
                                                             "container-D_1.0"])

        self.app.uninstallPackages(["container-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_2.0",
                                                             "container-C_1.0",
                                                             "container-D_1.0"])

        self.app.uninstallPackages(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testBadContainer(self):
        with self.assertRaises(Exception):
            self.app.installFromRemotes(["failure-depends-leaf_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testContainerNotMaster(self):
        self.app.installFromRemotes(["container-A_1.1"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_1.1",
                                                             "container-B_1.0",
                                                             "container-C_1.0",
                                                             "container-E_1.0"])

        self.app.installFromRemotes(["container-A_2.1"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_1.1",
                                                             "container-B_1.0",
                                                             "container-C_1.0",
                                                             "container-E_1.0",
                                                             "container-A_2.1",
                                                             "container-D_1.0"])

        self.app.uninstallPackages(["container-A_1.1"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_2.1",
                                                             "container-C_1.0",
                                                             "container-D_1.0"])

        self.app.uninstallPackages(["container-A_2.1"])
        self.checkContent(self.app.listInstalledPackages(), [])

    def testSteps(self):
        self.app.installFromRemotes(["install_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["install_1.0"])

        folder = self.getInstallFolder() / "install_1.0"

        self.assertTrue(folder.is_dir())
        self.assertTrue((folder / "data1").is_file())
        self.assertTrue((folder / "folder").is_dir())
        self.assertTrue((folder / "folder" / "data2").is_file())
        self.assertTrue((folder / "folder" / "data1-symlink").is_symlink())

        self.assertFalse((self.getInstallFolder() / "uninstall.log").is_file())
        self.assertTrue((folder / "postinstall.log").is_file())
        self.assertTrue((folder / "targetFileFromEnv").is_file())
        self.assertTrue((folder / "dump.env").is_file())
        self.assertTrue((folder / "folder2").is_dir())
        with open(str(folder / "targetFileFromEnv"), 'r') as fp:
            content = fp.read().splitlines()
            self.assertEqual(1, len(content))
            self.assertEqual(str(folder), content[0])

        self.app.uninstallPackages(["install_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])
        self.assertTrue((self.getInstallFolder() / "uninstall.log").is_file())

    def testPostinstallError(self):
        with self.assertRaises(Exception):
            self.app.installFromRemotes(["failure-postinstall-exec_1.0"],
                                        keepFolderOnError=True)
        found = False
        for folder in self.getInstallFolder().iterdir():
            if folder.name.startswith("failure-postinstall-exec_1.0"):
                self.assertTrue(isFolderIgnored(folder))
                found = True
                break
        self.assertTrue(found)

    def testInstallLatest(self):
        self.app.installFromRemotes(["version"])
        self.checkContent(self.app.listInstalledPackages(), ["version_2.0"])

    def testCannotUninstallToKeepDependencies(self):
        self.app.installFromRemotes(["container-A_2.0"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_2.0",
                                                             "container-C_1.0",
                                                             "container-D_1.0"])

        self.app.uninstallPackages(["container-C_1.0"])
        self.checkContent(self.app.listInstalledPackages(), ["container-A_2.0",
                                                             "container-C_1.0",
                                                             "container-D_1.0"])

    def testEnv(self):
        self.app.installFromRemotes(["env-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["env-A_1.0",
                           "env-B_1.0"])

        env = self.app.getPackageEnv(["env-A_1.0"])
        self.assertEqual(9, len(env.toList()))
        self.assertEqual([
            ("LEAF_VERSION", "0.0.0"),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
                            (self.getInstallFolder(), self.getInstallFolder()))],
            env.toList())

    def testSilentFail(self):
        with self.assertRaises(Exception):
            self.app.installFromRemotes(["failure-postinstall-exec_1.0"])
        self.checkContent(self.app.listInstalledPackages(), [])

        self.app.installFromRemotes(["failure-postinstall-exec-silent_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["failure-postinstall-exec-silent_1.0"])

    def testResolveLastVersion(self):
        self.app.installFromRemotes(["container-A_2.0"])
        self.assertEqual([PackageIdentifier.fromString("container-A_2.0")],
                         self.app.resolveLatest(["container-A"],
                                                ipMap=True))
        self.assertEqual([PackageIdentifier.fromString("container-A_2.1")],
                         self.app.resolveLatest(["container-A"],
                                                apMap=True))
        with self.assertRaises(Exception):
            self.app.resolveLatest(["container-A"])

    def testOutdatedCacheFile(self):

        def getMtime():
            return self.app.remoteCacheFile.stat().st_mtime

        # Initial refresh
        self.app.fetchRemotes(smartRefresh=True)
        previousMtime = getMtime()

        # Second refresh, same day, file should not be updated
        time.sleep(1)
        self.app.fetchRemotes(smartRefresh=True)
        self.assertEqual(previousMtime, getMtime())
        os.remove(str(self.app.remoteCacheFile))
        self.assertFalse(self.app.remoteCacheFile.exists())

        # File has been deleted
        time.sleep(1)
        self.app.fetchRemotes(smartRefresh=True)
        self.assertNotEqual(previousMtime, getMtime())
        previousMtime = getMtime()

        # Initial refresh
        time.sleep(1)
        self.app.fetchRemotes(smartRefresh=True)
        self.assertEqual(previousMtime, getMtime())

        # New refresh, 23h ago, file should not be updated
        time.sleep(1)
        today = datetime.now()
        almostyesterday = today - timedelta(hours=23)
        os.utime(str(self.app.remoteCacheFile), (int(almostyesterday.timestamp()),
                                                 int(almostyesterday.timestamp())))
        self.assertNotEqual(previousMtime, getMtime())
        previousMtime = getMtime()
        self.app.fetchRemotes(smartRefresh=True)
        self.assertEqual(previousMtime, getMtime())

        # New refresh, 24h ago, file should be updated
        time.sleep(1)
        yesterday = today - timedelta(hours=24)
        os.utime(str(self.app.remoteCacheFile), (int(yesterday.timestamp()),
                                                 int(yesterday.timestamp())))
        self.assertNotEqual(previousMtime, getMtime())
        previousMtime = getMtime()
        self.app.fetchRemotes(smartRefresh=True)
        self.assertNotEqual(previousMtime, getMtime())

    def testConditionalInstall(self):
        self.app.installFromRemotes(["condition_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["condition_1.0",
                           "condition-B_1.0",
                           "condition-D_1.0",
                           "condition-F_1.0",
                           "condition-H_1.0"])

        self.app.installFromRemotes(["condition_1.0"],
                                    env=Environment("test",
                                                    {"FOO": "BAR"}))
        self.checkContent(self.app.listInstalledPackages(),
                          ["condition_1.0",
                           "condition-A_1.0",
                           "condition-B_1.0",
                           "condition-C_1.0",
                           "condition-D_1.0",
                           "condition-F_1.0",
                           "condition-H_1.0"])

        self.app.updateUserConfiguration(envSetMap={"FOO2": "BAR2",
                                                    "HELLO": "WoRld"})

        env = self.app.getLeafEnvironment()
        env.addSubEnv(Environment("test", {"FOO": "BAR"}))
        self.app.installFromRemotes(["condition_1.0"],
                                    env=env)
        self.checkContent(self.app.listInstalledPackages(),
                          ["condition_1.0",
                           "condition-A_1.0",
                           "condition-B_1.0",
                           "condition-C_1.0",
                           "condition-D_1.0",
                           "condition-E_1.0",
                           "condition-F_1.0",
                           "condition-G_1.0",
                           "condition-H_1.0"])

        self.app.uninstallPackages(["condition_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          [])

    def testPrereqRoot(self):
        motifList = ["prereq-A_1.0",
                     "prereq-B_1.0",
                     "prereq-C_1.0",
                     "prereq-D_1.0",
                     "prereq-true_1.0",
                     "prereq-env_1.0",
                     "prereq-false_1.0"]
        errorCount = self.app.installPrereqFromRemotes(motifList,
                                                       self.getAltWorkspaceFolder(),
                                                       raiseOnError=False)
        self.assertEqual(1, errorCount)
        for m in motifList:
            self.assertEqual("false" not in m,
                             (self.getAltWorkspaceFolder() / m).is_dir())

    def testPrereqA(self):
        self.app.installFromRemotes(["prereq-A_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["prereq-A_1.0"])

    def testPrereqB(self):
        self.app.installFromRemotes(["prereq-B_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["prereq-A_1.0",
                           "prereq-B_1.0"])

    def testPrereqC(self):
        self.app.installFromRemotes(["prereq-C_1.0"])
        self.checkContent(self.app.listInstalledPackages(),
                          ["prereq-C_1.0",
                           "prereq-true_1.0"])

    def testPrereqD(self):
        with self.assertRaises(ValueError):
            self.app.installFromRemotes(["prereq-D_1.0"])

    def testPrereqEnv(self):
        motifList = ["prereq-env_1.0"]
        errorCount = self.app.installPrereqFromRemotes(motifList,
                                                       self.getAltWorkspaceFolder(),
                                                       raiseOnError=False)
        self.assertEqual(0, errorCount)
        envDumpFile = self.getAltWorkspaceFolder() / "prereq-env_1.0" / "dump.env"
        self.assertTrue(envDumpFile.exists())
        env = envFileToMap(envDumpFile)
        self.assertEqual(env["LEAF_PREREQ_ROOT"],
                         str(self.getAltWorkspaceFolder()))

    def testDependsAvailable(self):
        self.assertDeps(self.app.listDependencies(
            ["container-A_3.0"], DependencyType.AVAILABLE),
            [],
            AvailablePackage)

        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.AVAILABLE),
            ["container-E_1.0",
             "container-B_1.0",
             "container-C_1.0",
             "container-A_1.0"],
            AvailablePackage)

    def testDependsInstall(self):
        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.INSTALL),
            ["container-E_1.0",
             "container-B_1.0",
             "container-C_1.0",
             "container-A_1.0"],
            AvailablePackage)

        self.app.installFromRemotes(["container-A_1.0"])

        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.INSTALL),
            [],
            AvailablePackage)

        self.assertDeps(self.app.listDependencies(
            ["container-A_2.0"], DependencyType.INSTALL),
            ["container-D_1.0",
             "container-A_2.0"],
            AvailablePackage)

    def testDependsInstalled(self):
        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.INSTALLED),
            [],
            InstalledPackage)

        self.app.installFromRemotes(["container-A_1.0"])

        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.INSTALLED),
            ["container-E_1.0",
             "container-B_1.0",
             "container-C_1.0",
             "container-A_1.0"],
            InstalledPackage)

    def testDependsUninstall(self):
        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.UNINSTALL),
            [],
            AvailablePackage)

        self.app.installFromRemotes(["container-A_1.0"])

        self.assertDeps(self.app.listDependencies(
            ["container-A_1.0"], DependencyType.UNINSTALL),
            ["container-A_1.0",
             "container-C_1.0",
             "container-B_1.0",
             "container-E_1.0"],
            InstalledPackage)

    def testDependsPrereq(self):
        self.assertDeps(self.app.listDependencies(
            ["prereq-D_1.0"], DependencyType.PREREQ),
            ["prereq-false_1.0",
             "prereq-true_1.0"],
            AvailablePackage)

    def assertDeps(self, result, expected, itemType):
        for item in result:
            self.assertEqual(itemType, type(item))
            self.assertTrue(isinstance(item, itemType))
        deps = [str(mf.getIdentifier()) for mf in result]
        self.assertEqual(expected, deps)


if __name__ == "__main__":
    unittest.main()
