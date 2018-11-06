'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os
import socketserver
import sys
import time
from builtins import ValueError
from datetime import datetime, timedelta
from multiprocessing import Process
from time import sleep

import unittest
from http.server import SimpleHTTPRequestHandler
from tests.testutils import AbstractTestWithRepo, envFileToMap, getLines, LEAF_UT_SKIP

from leaf.constants import EnvConstants
from leaf.core.dependencies import DependencyType
from leaf.core.error import InvalidHashException, InvalidPackageNameException, \
    NoEnabledRemoteException, NoRemoteException
from leaf.core.features import FeatureManager
from leaf.core.packagemanager import PackageManager
from leaf.format.logger import Verbosity
from leaf.model.environment import Environment
from leaf.model.package import AvailablePackage, InstalledPackage, \
    PackageIdentifier
from leaf.utils import isFolderIgnored


VERBOSITY = Verbosity.VERBOSE
HTTP_PORT = os.environ.get("LEAF_HTTP_PORT", "54940")

# Needed for http server
sys.path.insert(0, os.path.abspath('../..'))


class TestApiPackageManager(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)

        self.pm = PackageManager(VERBOSITY)

        if EnvConstants.DOWNLOAD_TIMEOUT not in os.environ:
            # Fix CI timeout
            os.environ[EnvConstants.DOWNLOAD_TIMEOUT] = "30"
            print("Override %s=%s" % (EnvConstants.DOWNLOAD_TIMEOUT,
                                      os.environ[EnvConstants.DOWNLOAD_TIMEOUT]),
                  file=sys.stderr)

        self.pm.setInstallFolder(self.getInstallFolder())
        with self.assertRaises(NoRemoteException):
            self.pm.listAvailablePackages()
        self.assertEqual(0, len(self.pm.listInstalledPackages()))
        with self.assertRaises(NoRemoteException):
            self.pm.listRemotes()
        self.assertEqual(0, len(self.pm.readConfiguration().getRemotesMap()))

        self.pm.createRemote("default", self.getRemoteUrl(), insecure=True)
        self.pm.createRemote("other", self.getRemoteUrl2(), insecure=True)
        self.assertEqual(2, len(self.pm.readConfiguration().getRemotesMap()))
        self.pm.fetchRemotes(True)
        self.assertEqual(2, len(self.pm.listRemotes()))
        self.assertTrue(self.pm.listRemotes()["default"].isFetched())
        self.assertTrue(self.pm.listRemotes()["other"].isFetched())
        self.assertNotEqual(0, len(self.pm.listAvailablePackages()))

    def testCompression(self):
        pisList = ["compress-bz2_1.0",
                   "compress-gz_1.0",
                   "compress-tar_1.0",
                   "compress-xz_1.0"]
        self.pm.installFromRemotes(PackageIdentifier.fromStringList(pisList))
        self.checkContent(self.pm.listInstalledPackages(), pisList)

    def testEnableDisableRemote(self):
        self.assertEqual(2, len(self.pm.listRemotes(True)))
        self.assertTrue(len(self.pm.listAvailablePackages()) > 0)

        remote = self.pm.listRemotes()["default"]
        remote.setEnabled(False)
        self.pm.updateRemote(remote)
        self.assertEqual(2, len(self.pm.listRemotes(False)))
        self.assertEqual(1, len(self.pm.listRemotes(True)))
        self.assertTrue(len(self.pm.listAvailablePackages()) == 1)

        remote = self.pm.listRemotes()["other"]
        remote.setEnabled(False)
        self.pm.updateRemote(remote)
        self.assertEqual(2, len(self.pm.listRemotes(False)))
        with self.assertRaises(NoEnabledRemoteException):
            self.pm.listRemotes(True)
        with self.assertRaises(NoEnabledRemoteException):
            self.pm.listAvailablePackages()

        remote = self.pm.listRemotes()["default"]
        remote.setEnabled(True)
        self.pm.updateRemote(remote)
        remote = self.pm.listRemotes()["other"]
        remote.setEnabled(True)
        self.pm.updateRemote(remote)
        self.assertEqual(2, len(self.pm.listRemotes(False)))
        self.assertEqual(2, len(self.pm.listRemotes(True)))
        self.assertTrue(len(self.pm.listAvailablePackages()) > 0)

    def testContainer(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_1.0",
                                                            "container-B_1.0",
                                                            "container-C_1.0",
                                                            "container-E_1.0"])

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_2.0"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_1.0",
                                                            "container-B_1.0",
                                                            "container-C_1.0",
                                                            "container-E_1.0",
                                                            "container-A_2.0",
                                                            "container-D_1.0"])

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_2.0",
                                                            "container-C_1.0",
                                                            "container-D_1.0"])

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["container-A_2.0"]))
        self.checkContent(self.pm.listInstalledPackages(), [])

    def testInstallUnknownPackage(self):
        with self.assertRaises(InvalidPackageNameException):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["unknwonPackage"]))
        with self.assertRaises(InvalidPackageNameException):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["container-A"]))
        with self.assertRaises(InvalidPackageNameException):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["unknwonPackage_1.0"]))

    def testBadContainer(self):
        with self.assertRaises(Exception):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["failure-depends-leaf_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), [])

    def testContainerNotMaster(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_1.1"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_1.1",
                                                            "container-B_1.0",
                                                            "container-C_1.0",
                                                            "container-E_1.0"])

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_1.1",
                                                            "container-B_1.0",
                                                            "container-C_1.0",
                                                            "container-E_1.0",
                                                            "container-A_2.1",
                                                            "container-D_1.0"])

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["container-A_1.1"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_2.1",
                                                            "container-C_1.0",
                                                            "container-D_1.0"])

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        self.checkContent(self.pm.listInstalledPackages(), [])

    def testSteps(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["install_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), ["install_1.0"])

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

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["install_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), [])
        self.assertTrue((self.getInstallFolder() / "uninstall.log").is_file())

    def testPostinstallError(self):
        with self.assertRaises(Exception):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(
                    ["failure-postinstall-exec_1.0"]),
                keepFolderOnError=True)
        found = False
        for folder in self.getInstallFolder().iterdir():
            if folder.name.startswith("failure-postinstall-exec_1.0"):
                self.assertTrue(isFolderIgnored(folder))
                found = True
                break
        self.assertTrue(found)

    def testCannotUninstallToKeepDependencies(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_2.0"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_2.0",
                                                            "container-C_1.0",
                                                            "container-D_1.0"])

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["container-C_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), ["container-A_2.0",
                                                            "container-C_1.0",
                                                            "container-D_1.0"])

    def testEnv(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["env-A_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["env-A_1.0",
                           "env-B_1.0"])

        env = self.pm.getPackagesEnvironment(
            PackageIdentifier.fromStringList(["env-A_1.0"]))
        self.assertEqual(2, len(env.toList()))
        self.assertEqual([
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
                            (self.getInstallFolder(), self.getInstallFolder()))],
            env.toList())

        env = self.pm.getPackagesEnvironment(
            PackageIdentifier.fromStringList(["env-B_1.0", "env-A_1.0"]))
        self.assertEqual(4, len(env.toList()))
        self.assertEqual([
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
                            (self.getInstallFolder(), self.getInstallFolder()))],
            env.toList())

    def testSilentFail(self):
        with self.assertRaises(Exception):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["failure-postinstall-exec_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(), [])

        self.pm.installFromRemotes(PackageIdentifier.fromStringList(
            ["failure-postinstall-exec-silent_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["failure-postinstall-exec-silent_1.0"])

    def testCannotInstallBadHash(self):
        with self.assertRaises(InvalidHashException):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["failure-badhash_1.0"]))

    def testOutdatedCacheFile(self):

        def getMtime():
            return self.pm.remoteCacheFile.stat().st_mtime

        # Initial refresh
        self.pm.fetchRemotes(smartRefresh=True)
        previousMtime = getMtime()

        # Second refresh, same day, file should not be updated
        time.sleep(1)
        self.pm.fetchRemotes(smartRefresh=True)
        self.assertEqual(previousMtime, getMtime())
        os.remove(str(self.pm.remoteCacheFile))
        self.assertFalse(self.pm.remoteCacheFile.exists())

        # File has been deleted
        time.sleep(1)
        self.pm.fetchRemotes(smartRefresh=True)
        self.assertNotEqual(previousMtime, getMtime())
        previousMtime = getMtime()

        # Initial refresh
        time.sleep(1)
        self.pm.fetchRemotes(smartRefresh=True)
        self.assertEqual(previousMtime, getMtime())

        # New refresh, 23h ago, file should not be updated
        time.sleep(1)
        today = datetime.now()
        almostyesterday = today - timedelta(hours=23)
        os.utime(str(self.pm.remoteCacheFile), (int(almostyesterday.timestamp()),
                                                int(almostyesterday.timestamp())))
        self.assertNotEqual(previousMtime, getMtime())
        previousMtime = getMtime()
        self.pm.fetchRemotes(smartRefresh=True)
        self.assertEqual(previousMtime, getMtime())

        # New refresh, 24h ago, file should be updated
        time.sleep(1)
        yesterday = today - timedelta(hours=24)
        os.utime(str(self.pm.remoteCacheFile), (int(yesterday.timestamp()),
                                                int(yesterday.timestamp())))
        self.assertNotEqual(previousMtime, getMtime())
        previousMtime = getMtime()
        self.pm.fetchRemotes(smartRefresh=True)
        self.assertNotEqual(previousMtime, getMtime())

    def testConditionalInstall(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["condition_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["condition_1.0",
                           "condition-B_1.0",
                           "condition-D_1.0",
                           "condition-F_1.0",
                           "condition-H_1.0"])

        self.pm.installFromRemotes(PackageIdentifier.fromStringList(["condition_1.0"]),
                                   env=Environment("test",
                                                   {"FOO": "BAR"}))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["condition_1.0",
                           "condition-A_1.0",
                           "condition-B_1.0",
                           "condition-C_1.0",
                           "condition-D_1.0",
                           "condition-F_1.0",
                           "condition-H_1.0"])

        self.pm.updateUserEnv(setMap={"FOO2": "BAR2",
                                      "HELLO": "WoRld"})

        env = Environment.build(self.pm.getLeafEnvironment(),
                                self.pm.getUserEnvironment(),
                                Environment("test", {"FOO": "BAR"}))
        self.pm.installFromRemotes(PackageIdentifier.fromStringList(["condition_1.0"]),
                                   env=env)
        self.checkContent(self.pm.listInstalledPackages(),
                          ["condition_1.0",
                           "condition-A_1.0",
                           "condition-B_1.0",
                           "condition-C_1.0",
                           "condition-D_1.0",
                           "condition-E_1.0",
                           "condition-F_1.0",
                           "condition-G_1.0",
                           "condition-H_1.0"])

        self.pm.uninstallPackages(
            PackageIdentifier.fromStringList(["condition_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          [])

    def testPrereqRoot(self):
        motifList = ["prereq-A_1.0",
                     "prereq-B_1.0",
                     "prereq-C_1.0",
                     "prereq-D_1.0",
                     "prereq-true_1.0",
                     "prereq-env_1.0",
                     "prereq-false_1.0"]
        errorCount = self.pm.installPrereqFromRemotes(PackageIdentifier.fromStringList(motifList),
                                                      self.getAltWorkspaceFolder(),
                                                      raiseOnError=False)
        self.assertEqual(1, errorCount)
        for m in motifList:
            self.assertEqual("false" not in m,
                             (self.getAltWorkspaceFolder() / m).is_dir())

    def testPrereqA(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["prereq-A_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["prereq-A_1.0"])

    def testPrereqB(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["prereq-B_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["prereq-A_1.0",
                           "prereq-B_1.0"])

    def testPrereqC(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["prereq-C_1.0"]))
        self.checkContent(self.pm.listInstalledPackages(),
                          ["prereq-C_1.0",
                           "prereq-true_1.0"])

    def testPrereqD(self):
        with self.assertRaises(ValueError):
            self.pm.installFromRemotes(
                PackageIdentifier.fromStringList(["prereq-D_1.0"]))

    def testPrereqEnv(self):
        motifList = ["prereq-env_1.0"]
        errorCount = self.pm.installPrereqFromRemotes(PackageIdentifier.fromStringList(motifList),
                                                      self.getAltWorkspaceFolder(),
                                                      raiseOnError=False)
        self.assertEqual(0, errorCount)
        envDumpFile = self.getAltWorkspaceFolder() / "prereq-env_1.0" / "dump.env"
        self.assertTrue(envDumpFile.exists())
        env = envFileToMap(envDumpFile)
        self.assertEqual(env["LEAF_PREREQ_ROOT"],
                         str(self.getAltWorkspaceFolder()))

    def testDependsAvailable(self):
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_3.0"]),
                DependencyType.AVAILABLE),
            [],
            AvailablePackage)

        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.AVAILABLE),
            ["container-E_1.0",
             "container-B_1.0",
             "container-C_1.0",
             "container-A_1.0"],
            AvailablePackage)

    def testDependsWithCustomEnv(self):
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                DependencyType.INSTALL,
                envMap={}),
            ["condition-B_1.0",
             "condition-D_1.0",
             "condition-F_1.0",
             "condition-H_1.0",
             "condition_1.0"],
            AvailablePackage)

        self.pm.updateUserEnv(setMap={'FOO': 'HELLO'})
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                DependencyType.INSTALL,
                envMap={}),
            ["condition-A_1.0",
             "condition-D_1.0",
             "condition-F_1.0",
             "condition-H_1.0",
             "condition_1.0"],
            AvailablePackage)

        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                DependencyType.INSTALL,
                envMap={'FOO': 'BAR'}),
            ["condition-A_1.0",
             "condition-C_1.0",
             "condition-F_1.0",
             "condition_1.0"],
            AvailablePackage)

    def testDependsInstall(self):
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.INSTALL),
            ["container-E_1.0",
             "container-B_1.0",
             "container-C_1.0",
             "container-A_1.0"],
            AvailablePackage)

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_1.0"]))

        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.INSTALL),
            [],
            AvailablePackage)

        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_2.0"]),
                DependencyType.INSTALL),
            ["container-D_1.0",
             "container-A_2.0"],
            AvailablePackage)

    def testDependsInstalled(self):
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.INSTALLED),
            [],
            InstalledPackage)

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_1.0"]))

        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.INSTALLED),
            ["container-E_1.0",
             "container-B_1.0",
             "container-C_1.0",
             "container-A_1.0"],
            InstalledPackage)

    def testDependsUninstall(self):
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.UNINSTALL),
            [],
            AvailablePackage)

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["container-A_1.0"]))

        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["container-A_1.0"]),
                DependencyType.UNINSTALL),
            ["container-A_1.0",
             "container-C_1.0",
             "container-B_1.0",
             "container-E_1.0"],
            InstalledPackage)

    def testDependsPrereq(self):
        self.assertDeps(
            self.pm.listDependencies(
                PackageIdentifier.fromStringList(["prereq-D_1.0"]),
                DependencyType.PREREQ),
            ["prereq-false_1.0",
             "prereq-true_1.0"],
            AvailablePackage)

    def assertDeps(self, result, expected, itemType):
        for item in result:
            self.assertEqual(itemType, type(item))
            self.assertTrue(isinstance(item, itemType))
        deps = [str(mf.getIdentifier()) for mf in result]
        self.assertEqual(expected, deps)

    def testFeatures(self):
        apMap = self.pm.listAvailablePackages()
        pkg = apMap.get(PackageIdentifier.fromString("condition_1.0"))
        self.assertEqual(4, len(pkg.getFeatures()))
        self.assertEqual(4, len(pkg.getFeaturesMap()))
        fm = FeatureManager(self.pm)
        self.assertEqual(5, len(fm.features))
        fm.getFeature("myFeatureFoo").check()
        fm.getFeature("myFeatureHello").check()
        fm.getFeature("featureWithDups").check()
        with self.assertRaises(ValueError):
            fm.getFeature("featureWithMultipleKeys").check()

    def testSync(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["sync_1.0"]))
        self.checkContent(
            self.pm.listInstalledPackages(),
            ["sync_1.0"])
        self.checkInstalledPackages(["sync_1.0"])
        syncFile = self.getInstallFolder() / "sync_1.0" / "sync.log"

        self.assertFalse(syncFile.exists())

        self.pm.syncPackages(PackageIdentifier.fromStringList(["sync_1.0"]))
        self.assertTrue(syncFile.exists())
        self.assertEqual([""],
                         getLines(syncFile))

        self.pm.syncPackages(PackageIdentifier.fromStringList(["sync_1.0"]))
        self.assertTrue(syncFile.exists())
        self.assertEqual(["",
                          ""],
                         getLines(syncFile))

        self.pm.updateUserEnv({"MYVAR2": "MYOTHERVALUE"})
        self.pm.syncPackages(PackageIdentifier.fromStringList(["sync_1.0"]))
        self.assertTrue(syncFile.exists())
        self.assertEqual(["",
                          "",
                          "MYOTHERVALUE"],
                         getLines(syncFile))

    def testResolveLatest(self):
        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["version_1.0"]))
        self.checkContent(
            self.pm.listInstalledPackages(),
            ["version_1.0"])
        self.checkInstalledPackages(
            ["version_1.0"])

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["version_1.1"]))
        self.checkContent(
            self.pm.listInstalledPackages(),
            ["version_1.0",
             "version_1.1"])
        self.checkInstalledPackages(
            ["version_1.0",
             "version_1.1"])

        env = self.pm.getPackagesEnvironment(
            PackageIdentifier.fromStringList(["version_latest"]))
        self.assertEqual("1.1", env.findValue("TEST_VERSION"))

        self.pm.installFromRemotes(
            PackageIdentifier.fromStringList(["version_latest"]))
        self.checkContent(
            self.pm.listInstalledPackages(),
            ["version_1.0",
             "version_1.1",
             "version_2.0"])
        self.checkInstalledPackages(
            ["version_1.0",
             "version_1.1",
             "version_2.0"])

        env = self.pm.getPackagesEnvironment(
            PackageIdentifier.fromStringList(["version_latest"]))
        self.assertEqual("2.0", env.findValue("TEST_VERSION"))


def startHttpServer(rootFolder):
    print("Start http server for %s on port %s" %
          (rootFolder, HTTP_PORT), file=sys.stderr)
    os.chdir(str(rootFolder))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", int(HTTP_PORT)),
                                   SimpleHTTPRequestHandler)
    httpd.serve_forever()


@unittest.skipIf("HTTP" in LEAF_UT_SKIP, "Test disabled")
class TestApiPackageManagerHttp(TestApiPackageManager):

    def __init__(self, methodName):
        TestApiPackageManager.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        TestApiPackageManager.setUpClass()
        print("Using http port %s" % HTTP_PORT, file=sys.stderr)
        TestApiPackageManagerHttp.process = Process(target=startHttpServer,
                                                    args=(AbstractTestWithRepo.REPO_FOLDER,))
        TestApiPackageManagerHttp.process.start()
        # Wait 10 seconds for the http server to start
        sleep(10)

    @classmethod
    def tearDownClass(cls):
        TestApiPackageManager.tearDownClass()
        print("Stopping http server ...", file=sys.stderr)
        TestApiPackageManagerHttp.process.terminate()
        TestApiPackageManagerHttp.process.join()
        print("Stopping http server ... done", file=sys.stderr)

    def getRemoteUrl(self):
        return "http://localhost:%s/index.json" % HTTP_PORT

    def getRemoteUrl2(self):
        return "http://localhost:%s/index2.json" % HTTP_PORT
