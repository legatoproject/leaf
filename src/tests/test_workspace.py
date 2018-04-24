'''
@author: seb
'''

from collections import OrderedDict
from leaf.core import Workspace, LeafApp
from leaf.logger import createLogger
import platform
import unittest

from tests.utils import AbstractTestWithRepo

VERBOSE = True


class TestProfile(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.logger = createLogger(VERBOSE, False, True)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.app = LeafApp(self.logger,
                           self.getConfigurationFile(),
                           self.getRemoteCacheFile())
        self.app.updateUserConfiguration(rootFolder=self.getInstallFolder(),
                                         remoteAddList=[self.getRemoteUrl()])
        self.ws = Workspace(self.getWorkspaceFolder(), self.app)

    def testInit(self):
        with self.assertRaises(Exception):
            self.ws.createProfile()
        self.ws.readConfiguration(True)
        self.ws.createProfile("foo")

    def testAddDeleteProfile(self):
        self.ws.readConfiguration(True)
        self.ws.createProfile("foo")
        self.assertEqual(1, len(self.ws.getAllProfiles()))

        with self.assertRaises(Exception):
            self.ws.createProfile("foo")

        self.ws.createProfile("bar")
        self.assertEqual(2, len(self.ws.getAllProfiles()))

        with self.assertRaises(Exception):
            self.ws.createProfile("bar")

        self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.getAllProfiles()))

        with self.assertRaises(Exception):
            self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.getAllProfiles()))

    def testUpdatetProfile(self):
        self.ws.readConfiguration(True)
        pf = self.ws.createProfile("foo")
        self.assertEqual([], pf.getPackages())
        self.assertEqual(OrderedDict(), pf.getEnvMap())

        self.ws.updateProfile("foo",
                              mpkgAddList=["container-A_1.0"],
                              envSetMap=OrderedDict([("FOO", "BAR"),
                                                     ("FOO2", "BAR2")]))
        pf = self.ws.retrieveProfile("foo")
        self.assertEqual(["container-A_1.0"],
                         pf.getPackages())
        self.assertEqual(OrderedDict([("FOO", "BAR"),
                                      ("FOO2", "BAR2")]),
                         pf.getEnvMap())

        self.ws.updateProfile("foo",
                              mpkgAddList=["container-A"])
        pf = self.ws.retrieveProfile("foo")
        self.assertEqual(["container-A_2.1"],
                         pf.getPackages())

        self.ws.updateProfile("foo",
                              mpkgAddList=["env-A_1.0"])
        pf = self.ws.retrieveProfile("foo")
        self.assertEqual(["container-A_2.1",
                          "env-A_1.0"],
                         pf.getPackages())

        with self.assertRaises(Exception):
            self.ws.updateProfile("fooooooooo",
                                  mpkgAddList=["container-A_1.0",
                                               "container-A_2.0"],
                                  envSetMap={"FOO": "BAR",
                                             "FOO2": "BAR2"})

    def testRenameProfile(self):
        self.ws.readConfiguration(True)
        self.ws.createProfile("foo")
        self.ws.updateProfile("foo",
                              mpkgAddList=["container-A"],
                              envSetMap={"FOO": "BAR"})
        self.ws.provisionProfile("foo")
        self.assertEqual("foo",
                         self.ws.getCurrentProfileName())
        self.checkProfileContent("foo",
                                 ["container-A",
                                  "container-C",
                                  "container-D"])

        self.ws.updateProfile("foo", newName="bar")
        self.assertEqual(1, len(self.ws.getAllProfiles()))
        self.assertEqual("bar", self.ws.retrieveProfile("bar").name)
        self.assertEqual("bar", self.ws.getCurrentProfileName())
        self.checkProfileContent("bar", ["container-A",
                                         "container-C",
                                         "container-D"])
        self.ws.getProfileEnv("bar")

        self.ws.updateProfile("bar", newName="bar")
        self.assertEqual("bar", self.ws.getCurrentProfileName())
        self.assertEqual("bar", self.ws.retrieveProfile("bar").name)

    def testSwitchProfile(self):
        self.ws.readConfiguration(True)
        self.ws.createProfile("foo")
        self.ws.switchProfile("foo")
        self.assertEqual("foo",
                         self.ws.getCurrentProfileName())

        self.ws.createProfile("bar")
        self.ws.switchProfile("bar")
        self.assertEqual("bar",
                         self.ws.getCurrentProfileName())

    def testEnv(self):
        self.ws.readConfiguration(True)
        self.ws.createProfile("myenv")
        self.ws.updateProfile("myenv",
                              mpkgAddList=["env-A_1.0",
                                           "env-B_1.0"],
                              envSetMap=OrderedDict([("FOO", "BAR"),
                                                     ("FOO2", "BAR2")]))
        self.ws.switchProfile("myenv")
        self.ws.provisionProfile("myenv")
        env = self.ws.getProfileEnv("myenv")
        self.assertEqual(11, len(env.toList()))
        self.assertEqual([
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ('LEAF_WORKSPACE', self.getWorkspaceFolder()),
            ('LEAF_PROFILE', 'myenv'),
            ('FOO', 'BAR'),
            ('FOO2', 'BAR2'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            env.toList())

        self.ws.updateWorkspaceConfiguration(envSetMap={"HELLO": "world"})
        env = self.ws.getProfileEnv("myenv")
        self.assertEqual(12, len(env.toList()))
        self.assertEqual([
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ('LEAF_WORKSPACE', self.getWorkspaceFolder()),
            ('LEAF_PROFILE', 'myenv'),
            ('HELLO', 'world'),
            ('FOO', 'BAR'),
            ('FOO2', 'BAR2'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            env.toList())

    def testWithoutVersion(self):
        self.app.fetchRemotes()
        self.ws.readConfiguration(True)
        self.ws.createProfile("foo")
        pf = self.ws.updateProfile("foo",
                                   mpkgAddList=["container-A"],
                                   envSetMap={"FOO": "BAR"})
        self.assertEqual(["container-A_2.1"],
                         pf.getPackages())
        self.ws.provisionProfile("foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])
        self.ws.updateProfile("foo",
                              mpkgAddList=["container-A_1.0"])
        self.ws.provisionProfile("foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E"])

    def testRemoteInWorkspace(self):
        self.app.updateUserConfiguration(
            remoteRmList=self.app.readConfiguration().getRemotes())
        self.assertEqual(0, len(self.app.readConfiguration().getRemotes()))
        self.assertEqual(0, len(self.app.getRemoteRepositories()))
        self.assertEqual(0, len(self.app.listAvailablePackages()))

        self.ws.readConfiguration(True)
        self.ws.updateWorkspaceConfiguration(
            remoteAddList=[self.getRemoteUrl()])
        self.ws.createProfile("foo")
        self.ws.updateProfile("foo", mpkgAddList=["container-A"])
        self.ws.switchProfile("foo")
        self.ws.provisionProfile("foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])
        self.assertEqual(1, len(self.app.readConfiguration().getRemotes()))
        self.assertEqual(2, len(self.app.getRemoteRepositories()))

    def testUpgrade(self):
        self.ws.readConfiguration(True)
        pf = self.ws.createProfile("foo")
        self.assertEqual([], pf.getPackages())
        self.assertEqual(OrderedDict(), pf.getEnvMap())

        self.ws.updateProfile("foo",
                              mpkgAddList=["container-A_1.0",
                                           "version_1.0"])
        pf = self.ws.retrieveProfile("foo")
        self.assertEqual(["container-A_1.0",
                          "version_1.0"],
                         pf.getPackages())

        self.ws.updateProfile("foo",
                              mpkgAddList=pf.getPackageMap().keys())
        pf = self.ws.retrieveProfile("foo")
        self.assertEqual(["container-A_2.1",
                          "version_2.0"],
                         pf.getPackages())


if __name__ == "__main__":
    unittest.main()
