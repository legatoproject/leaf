'''
@author: seb
'''

from collections import OrderedDict
import platform
import unittest

import leaf
from leaf.core.features import FeatureManager
from leaf.format.logger import TextLogger, Verbosity
from leaf.core.packagemanager import PackageManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.model.package import PackageIdentifier, Manifest
from tests.test_depends import mkpi
from tests.testutils import AbstractTestWithRepo


VERBOSITY = Verbosity.VERBOSE


class TestProfile(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.logger = TextLogger(VERBOSITY, True)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.pm = PackageManager(self.logger, nonInteractive=True)
        self.pm.setInstallFolder(self.getInstallFolder())
        self.pm.createRemote("default", self.getRemoteUrl())
        self.ws = WorkspaceManager(self.getWorkspaceFolder(), self.pm)

    def testInit(self):
        with self.assertRaises(Exception):
            self.ws.createProfile()
        self.ws.inittialize()
        profile = self.ws.createProfile("foo")
        self.assertIsNotNone(profile)
        self.assertEqual("foo", profile.name)

    def testAddDeleteProfile(self):
        self.ws.inittialize()
        self.ws.createProfile("foo")
        self.assertEqual(1, len(self.ws.listProfiles()))

        with self.assertRaises(Exception):
            self.ws.createProfile("foo")

        self.ws.createProfile("bar")
        self.assertEqual(2, len(self.ws.listProfiles()))

        with self.assertRaises(Exception):
            self.ws.createProfile("bar")

        self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.listProfiles()))

        with self.assertRaises(Exception):
            self.ws.deleteProfile("foo")
        self.assertEqual(1, len(self.ws.listProfiles()))

    def testUpdatetProfile(self):
        self.ws.inittialize()
        profile = self.ws.createProfile("foo")
        self.assertEqual([], profile.getPackages())
        self.assertEqual(OrderedDict(), profile.getEnvMap())

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        profile.updateEnv(OrderedDict([("FOO", "BAR"),
                                       ("FOO2", "BAR2")]))
        profile = self.ws.updateProfile(profile)

        self.assertEqual(["container-A_1.0"],
                         profile.getPackages())
        self.assertEqual(OrderedDict([("FOO", "BAR"),
                                      ("FOO2", "BAR2")]),
                         profile.getEnvMap())

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        profile = self.ws.updateProfile(profile)
        self.assertEqual(["container-A_2.1"],
                         profile.getPackages())

        profile.addPackages(
            PackageIdentifier.fromStringList(["env-A_1.0"]))
        profile = self.ws.updateProfile(profile)
        self.assertEqual(["container-A_2.1",
                          "env-A_1.0"],
                         profile.getPackages())

        profile.removePackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        profile = self.ws.updateProfile(profile)
        self.assertEqual(["env-A_1.0"],
                         profile.getPackages())

        with self.assertRaises(Exception):
            profile.name = "fooooooo"
            self.ws.updateProfile(profile)

    def testRenameProfile(self):
        self.ws.inittialize()
        self.ws.createProfile("foo")

        with self.assertRaises(ValueError):
            self.ws.getCurrentProfileName()
        profile = self.ws.getProfile("foo")
        self.ws.switchProfile(profile)
        self.assertEqual("foo",
                         self.ws.getCurrentProfileName())

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        profile.updateEnv({"FOO": "BAR"})
        profile = self.ws.updateProfile(profile)

        self.ws.provisionProfile(profile)
        self.assertEqual("foo",
                         self.ws.getCurrentProfileName())

        self.checkProfileContent("foo",
                                 ["container-A",
                                  "container-C",
                                  "container-D"])

        profile = self.ws.renameProfile("foo", "bar")
        self.assertEqual(1, len(self.ws.listProfiles()))
        self.assertEqual("bar", profile.name)
        self.assertEqual("bar", self.ws.getProfile("bar").name)
        self.assertEqual("bar", self.ws.getCurrentProfileName())
        self.checkProfileContent("bar", ["container-A",
                                         "container-C",
                                         "container-D"])
        self.ws.getFullEnvironment(profile)
        with self.assertRaises(ValueError):
            self.ws.renameProfile("bar", "bar")
        with self.assertRaises(ValueError):
            self.ws.renameProfile("foo", "bar")

    def testSwitchProfile(self):
        self.ws.inittialize()
        profile = self.ws.createProfile("foo")
        self.ws.switchProfile(profile)
        self.assertEqual("foo",
                         self.ws.getCurrentProfileName())

        profile2 = self.ws.createProfile("bar")
        self.ws.switchProfile(profile2)
        self.assertEqual("bar",
                         self.ws.getCurrentProfileName())

    def testEnv(self):
        self.ws.inittialize()
        profile = self.ws.createProfile("myenv")
        profile.addPackages([PackageIdentifier.fromString(pis)
                             for pis in ["env-A_1.0", "env-A_1.0"]])
        profile = self.ws.updateProfile(profile)

        self.ws.switchProfile(profile)
        self.ws.provisionProfile(profile)

        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

        self.pm.updateUserEnv(setMap=OrderedDict(
            (("scope", "user"), ("HELLO", "world"))))
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('HELLO', 'world'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

        self.pm.updateUserEnv(unsetList=["HELLO"])
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

        self.ws.updateWorkspaceEnv(setMap=OrderedDict(
            (("scope", "workspace"), ("HELLO", "world"))))
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('scope', 'workspace'),
            ('HELLO', 'world'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

        self.ws.updateWorkspaceEnv(unsetList=["HELLO"])
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('scope', 'workspace'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

        profile.updateEnv(setMap=OrderedDict(
            (("scope", "profile"), ("HELLO", "world"))))
        profile = self.ws.updateProfile(profile)
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('scope', 'workspace'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('scope', 'profile'),
            ('HELLO', 'world'),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

        profile.updateEnv(unsetList=["HELLO"])
        profile = self.ws.updateProfile(profile)
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('scope', 'workspace'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('scope', 'profile'),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.ws.getFullEnvironment(profile).toList())

    def testPackageOverride(self):
        self.ws.inittialize()
        profile = self.ws.createProfile("myprofile")
        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        profile = self.ws.updateProfile(profile)
        self.ws.provisionProfile(profile)

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E"])

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-E_1.1"]))
        profile = self.ws.updateProfile(profile)
        self.ws.provisionProfile(profile)

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "container-E_1.1"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E"])
        self.assertEqual(list(map(mkpi,
                                  ["container-E_1.1",
                                   "container-B_1.0",
                                   "container-C_1.0",
                                   "container-A_1.0"])),
                         list(map(Manifest.getIdentifier,
                                  self.ws.getProfileDependencies(profile))))

    def testFeatures(self):
        fm = FeatureManager(self.pm)

        feature = fm.getFeature("myFeatureFoo")
        self.assertIsNotNone(feature)

        self.assertEqual("FOO",
                         feature.getKey())
        self.assertEqual({"bar": "BAR",
                          "notbar": "OTHER_VALUE"},
                         feature.getValues())

        self.assertEqual(None,
                         self.pm.getUserEnvironment().findValue("FOO"))
        fm.toggleUserFeature("myFeatureFoo", "bar", self.pm)
        self.assertEqual("BAR",
                         self.pm.getUserEnvironment().findValue("FOO"))

        self.ws.inittialize()
        self.assertEqual(None,
                         self.ws.getWorkspaceEnvironment().findValue("FOO"))
        fm.toggleWorkspaceFeature("myFeatureFoo", "bar", self.ws)
        self.assertEqual("BAR",
                         self.ws.getWorkspaceEnvironment().findValue("FOO"))

        profile = self.ws.createProfile("myprofile")
        self.ws.switchProfile(profile)
        self.assertEqual(None,
                         self.ws.getProfile("myprofile").getEnvironment().findValue("FOO"))
        fm.toggleProfileFeature("myFeatureFoo", "bar", self.ws)
        self.assertEqual("BAR",
                         self.ws.getProfile("myprofile").getEnvironment().findValue("FOO"))

        with self.assertRaises(ValueError):
            fm.toggleUserFeature("unknwonFeature", "unknownValue", self.pm)

        with self.assertRaises(ValueError):
            fm.toggleUserFeature("myFeatureFoo", "unknownValue", self.pm)

        # Error cases
        fm.toggleUserFeature("featureWithDups", "enum1", self.pm)
        with self.assertRaises(ValueError):
            fm.toggleUserFeature("featureWithDups", "enum2", self.pm)
        with self.assertRaises(ValueError):
            fm.toggleUserFeature("featureWithMultipleKeys", "enum1", self.pm)


if __name__ == "__main__":
    unittest.main()
