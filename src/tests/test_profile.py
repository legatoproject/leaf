'''
@author: seb
'''

from collections import OrderedDict
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import Workspace, LeafApp
from leaf.logger import createLogger
import unittest

from tests.utils import AbstractTestWithRepo


VERBOSE = True


class TestProfile(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.logger = createLogger(VERBOSE, False)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.app = LeafApp(self.logger,
                           self.getConfigurationFile(),
                           self.getRemoteCacheFile())
        self.app.remoteAdd(self.getRemoteUrl())
        self.app.updateConfiguration(self.getInstallFolder())
        self.ws = Workspace(self.getWorkspaceFolder(), self.app)

    def checkProfileContent(self, profileName, *content):
        pfFolder = self.getWorkspaceFolder() / LeafFiles.PROFILES_FOLDERNAME / profileName
        self.assertTrue(pfFolder.exists())
        symlinkCount = 0
        for item in pfFolder.iterdir():
            if item.is_symlink():
                symlinkCount += 1
            self.assertTrue(item.name in content, "Unexpected link %s" % item)
        self.assertEqual(symlinkCount, len(content))

    def testInit(self):
        with self.assertRaises(Exception):
            self.ws.createProfile(LeafConstants.DEFAULT_PROFILE)

        self.ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                              initConfigFile=True)

    def testAddDeleteProfile(self):
        self.ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                              initConfigFile=True)
        self.assertEqual(1, len(self.ws.getProfileMap()))

        with self.assertRaises(Exception):
            self.ws.createProfile(LeafConstants.DEFAULT_PROFILE)

        self.ws.createProfile("foo")
        self.assertEqual(2, len(self.ws.getProfileMap()))

        with self.assertRaises(Exception):
            self.ws.createProfile("foo")

        self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.getProfileMap()))

        with self.assertRaises(Exception):
            self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.getProfileMap()))

    def testUpdateDefaultProfile(self, name=LeafConstants.DEFAULT_PROFILE):
        pf = self.ws.createProfile(name,
                                   initConfigFile=True)
        self.assertEqual([], pf.getPackages())
        self.assertEqual(OrderedDict(), pf.getEnv())

        self.ws.updateProfile(name,
                              ["container-A_1.0"],
                              OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]))
        pf = self.ws.getProfile(name)
        self.assertEqual(["container-A_1.0"],
                         pf.getPackages())
        self.assertEqual(OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]),
                         pf.getEnv())

        self.ws.updateProfile(name,
                              ["container-A"])
        pf = self.ws.getProfile(name)
        self.assertEqual(["container-A_2.1"],
                         pf.getPackages())

        self.ws.updateProfile(name,
                              ["env-A_1.0"])
        pf = self.ws.getProfile(name)
        self.assertEqual(["container-A_2.1", "env-A_1.0"],
                         pf.getPackages())

        with self.assertRaises(Exception):
            self.ws.updateProfile("fooooooooo",
                                  ["container-A_1.0", "container-A_2.0"],
                                  {"FOO": "BAR", "FOO2": "BAR2"})

    def testUpdateNamedProfile(self):
        self.testUpdateDefaultProfile("foo")

    def testSwitchProfile(self):
        self.ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                              initConfigFile=True)

        with self.assertRaises(Exception):
            self.ws.getCurrentProfileName()

        with self.assertRaises(Exception):
            self.ws.switchProfile("foo")

        self.ws.switchProfile("default")

        self.assertEqual(LeafConstants.DEFAULT_PROFILE,
                         self.ws.getCurrentProfileName())

        self.ws.createProfile("foo")
        self.ws.switchProfile("foo")
        self.assertEqual("foo",
                         self.ws.getCurrentProfileName())

    def testEnv(self):
        self.ws.createProfile("myenv",
                              ["env-A_1.0",
                               "env-B_1.0"],
                              OrderedDict([("FOO", "BAR"),
                                           ("FOO2", "BAR2")]),
                              initConfigFile=True)
        self.app.fetchRemotes()
        self.ws.switchProfile("myenv")
        env = self.ws.getProfileEnv("myenv")
        self.assertEqual(7, len(env))
        self.assertEqual([
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder())),
            ('FOO', 'BAR'),
            ('FOO2', 'BAR2')],
            env)

    def testWithoutVersion(self):
        self.app.fetchRemotes()
        pf = self.ws.createProfile("foo",
                                   ["container-A"],
                                   {"FOO": "BAR"},
                                   initConfigFile=True)
        self.assertEqual(["container-A_2.1"], pf.getPackages())
        pf.getPackages()
        self.ws.switchProfile("foo")
        self.checkProfileContent("foo",
                                 "container-A",
                                 "container-C",
                                 "container-D")
        self.ws.updateProfile("foo", ["container-A_1.0"], None)
        self.ws.switchProfile("foo")
        self.checkProfileContent("foo",
                                 "container-A",
                                 "container-B",
                                 "container-C",
                                 "container-E")


if __name__ == "__main__":
    unittest.main()
