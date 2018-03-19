'''
@author: seb
'''

from collections import OrderedDict
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import Workspace, LeafApp
from leaf.logger import createLogger
import unittest

from tests.utils import TestWithRepository


VERBOSE = True


class TestProfile(TestWithRepository):

    def __init__(self, methodName):
        TestWithRepository.__init__(self, methodName)
        self.logger = createLogger(VERBOSE, False, False)

    def setUp(self):
        TestWithRepository.setUp(self)
        self.app = LeafApp(self.logger,
                           TestWithRepository.CONFIG_FILE,
                           TestWithRepository.CACHE_FILE)
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
        with self.assertRaises(Exception):
            self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.getProfileMap()))

    def testUpdateDefaultProfile(self):
        pf = self.ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                                   initConfigFile=True)
        self.assertEqual([], pf.getPackages())
        self.assertEqual(OrderedDict(), pf.getEnv())
        self.ws.updateProfile(LeafConstants.DEFAULT_PROFILE,
                              ["container-A_1.0",
                               "container-A_2.0"],
                              OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]))
        pf = self.ws.getProfile(LeafConstants.DEFAULT_PROFILE)
        self.assertEqual(["container-A_1.0", "container-A_2.0"],
                         pf.getPackages())
        self.assertEqual(OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]),
                         pf.getEnv())

        with self.assertRaises(Exception):
            self.ws.updateProfile("foo",
                                  ["container-A_1.0",
                                   "container-A_2.0"],
                                  {"FOO": "BAR", "FOO2": "BAR2"})

    def testUpdateNamedProfile(self):
        pf = self.ws.createProfile("foo",
                                   initConfigFile=True)
        self.assertEqual([], pf.getPackages())
        self.assertEqual(OrderedDict(), pf.getEnv())

        self.ws.updateProfile("foo",
                              ["container-A_1.0",
                               "container-A_2.0"],
                              OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]))
        pf = self.ws.getProfile("foo")
        self.assertEqual(["container-A_1.0", "container-A_2.0"],
                         pf.getPackages())
        self.assertEqual(OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]),
                         pf.getEnv())

    def testProvisionProfile(self):
        self.ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                              initConfigFile=True)
        self.ws.provisionProfile(LeafConstants.DEFAULT_PROFILE)
        self.ws.createProfile("foo",
                              ["container-A_1.0"],
                              initConfigFile=True)
        with self.assertRaises(Exception):
            self.ws.provisionProfile("foo")
        self.app.fetchRemotes()
        self.ws.provisionProfile("foo")

    def testSwitchProfile(self):
        self.ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                              initConfigFile=True)

        with self.assertRaises(Exception):
            self.ws.getCurrentProfileName()

        with self.assertRaises(Exception):
            self.ws.switchProfile(LeafConstants.DEFAULT_PROFILE)

        self.ws.provisionProfile(LeafConstants.DEFAULT_PROFILE)
        self.ws.switchProfile(LeafConstants.DEFAULT_PROFILE)
        self.assertEqual(LeafConstants.DEFAULT_PROFILE,
                         self.ws.getCurrentProfileName())

        self.ws.createProfile("foo")

        with self.assertRaises(Exception):
            self.ws.switchProfile("foo")

        self.ws.provisionProfile("foo")
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
        self.ws.provisionProfile("myenv")
        env = self.ws.getProfileEnv("myenv")
        self.assertEqual(6, len(env))
        self.assertEqual([
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
        self.ws.provisionProfile("foo")
        self.checkProfileContent("foo",
                                 "container-A",
                                 "container-C",
                                 "container-D")
        self.ws.updateProfile("foo", ["container-A_1.0"], None)
        self.ws.provisionProfile("foo")
        self.checkProfileContent("foo",
                                 "container-A",
                                 "container-A_1.0",
                                 "container-B",
                                 "container-C",
                                 "container-D",
                                 "container-E")


if __name__ == "__main__":
    unittest.main()
