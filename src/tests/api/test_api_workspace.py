'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import platform
from collections import OrderedDict

from tests.testutils import AbstractTestWithRepo

import leaf
from leaf.core.error import InvalidProfileNameException, NoProfileSelected, \
    ProfileNameAlreadyExistException
from leaf.core.features import FeatureManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.format.logger import TextLogger, Verbosity
from leaf.model.package import Manifest, PackageIdentifier


VERBOSITY = Verbosity.VERBOSE


class TestApiWorkspaceManager(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.logger = TextLogger(VERBOSITY)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.wm = WorkspaceManager(self.getWorkspaceFolder(), VERBOSITY)
        self.wm.setInstallFolder(self.getInstallFolder())
        self.wm.createRemote("default", self.getRemoteUrl(), insecure=True)
        self.wm.createRemote("other", self.getRemoteUrl2(), insecure=True)

    def testInit(self):
        with self.assertRaises(Exception):
            self.wm.createProfile("foo")
        self.wm.initializeWorkspace()
        profile = self.wm.createProfile("foo")
        self.assertIsNotNone(profile)
        self.assertEqual("foo", profile.name)

    def testAddDeleteProfile(self):
        self.wm.initializeWorkspace()
        self.wm.createProfile("foo")
        self.assertEqual(1, len(self.wm.listProfiles()))

        with self.assertRaises(Exception):
            self.wm.createProfile("foo")

        self.wm.createProfile("bar")
        self.assertEqual(2, len(self.wm.listProfiles()))

        with self.assertRaises(Exception):
            self.wm.createProfile("bar")

        self.wm.deleteProfile("foo")
        self.assertEqual(1, len(self.wm.listProfiles()))

        with self.assertRaises(Exception):
            self.wm.deleteProfile("foo")
        self.assertEqual(1, len(self.wm.listProfiles()))

    def testUpdatetProfile(self):
        self.wm.initializeWorkspace()
        profile = self.wm.createProfile("foo")
        self.assertEqual([], profile.getPackages())
        self.assertEqual(OrderedDict(), profile.getEnvMap())

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        profile.updateEnv(OrderedDict([("FOO", "BAR"),
                                       ("FOO2", "BAR2")]))
        profile = self.wm.updateProfile(profile)

        self.assertEqual(["container-A_1.0"],
                         profile.getPackages())
        self.assertEqual(OrderedDict([("FOO", "BAR"),
                                      ("FOO2", "BAR2")]),
                         profile.getEnvMap())

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        profile = self.wm.updateProfile(profile)
        self.assertEqual(["container-A_2.1"],
                         profile.getPackages())

        profile.addPackages(
            PackageIdentifier.fromStringList(["env-A_1.0"]))
        profile = self.wm.updateProfile(profile)
        self.assertEqual(["container-A_2.1",
                          "env-A_1.0"],
                         profile.getPackages())

        profile.removePackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        profile = self.wm.updateProfile(profile)
        self.assertEqual(["env-A_1.0"],
                         profile.getPackages())

        with self.assertRaises(Exception):
            profile.name = "fooooooo"
            self.wm.updateProfile(profile)

    def testRenameProfile(self):
        self.wm.initializeWorkspace()
        self.wm.createProfile("foo")

        with self.assertRaises(NoProfileSelected):
            self.wm.getCurrentProfileName()
        profile = self.wm.getProfile("foo")
        self.wm.switchProfile(profile)
        self.assertEqual("foo",
                         self.wm.getCurrentProfileName())

        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_2.1"]))
        profile.updateEnv({"FOO": "BAR"})
        profile = self.wm.updateProfile(profile)

        self.wm.provisionProfile(profile)
        self.assertEqual("foo",
                         self.wm.getCurrentProfileName())

        self.checkProfileContent("foo",
                                 ["container-A",
                                  "container-C",
                                  "container-D"])

        profile = self.wm.renameProfile("foo", "bar")
        self.assertEqual(1, len(self.wm.listProfiles()))
        self.assertEqual("bar", profile.name)
        self.assertEqual("bar", self.wm.getProfile("bar").name)
        self.assertEqual("bar", self.wm.getCurrentProfileName())
        self.checkProfileContent("bar", ["container-A",
                                         "container-C",
                                         "container-D"])
        self.wm.getFullEnvironment(profile)
        with self.assertRaises(ProfileNameAlreadyExistException):
            self.wm.renameProfile("bar", "bar")
        with self.assertRaises(InvalidProfileNameException):
            self.wm.renameProfile("foo", "bar")

    def testSwitchProfile(self):
        self.wm.initializeWorkspace()
        profile = self.wm.createProfile("foo")
        self.wm.switchProfile(profile)
        self.assertEqual("foo",
                         self.wm.getCurrentProfileName())

        profile2 = self.wm.createProfile("bar")
        self.wm.switchProfile(profile2)
        self.assertEqual("bar",
                         self.wm.getCurrentProfileName())

    def testEnv(self):
        self.wm.initializeWorkspace()
        profile = self.wm.createProfile("myenv")
        profile.addPackages([PackageIdentifier.fromString(pis)
                             for pis in ["env-A_1.0", "env-A_1.0"]])
        profile = self.wm.updateProfile(profile)

        self.wm.switchProfile(profile)
        self.wm.provisionProfile(profile)

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
            self.wm.getFullEnvironment(profile).toList())

        self.wm.updateUserEnv(setMap=OrderedDict(
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
            self.wm.getFullEnvironment(profile).toList())

        self.wm.updateUserEnv(unsetList=["HELLO"])
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
            self.wm.getFullEnvironment(profile).toList())

        self.wm.updateWorkspaceEnv(setMap=OrderedDict(
            (("scope", "workspace"), ("HELLO", "world"))))
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('scope', 'workspace'),
            ('HELLO', 'world'),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.wm.getFullEnvironment(profile).toList())

        self.wm.updateWorkspaceEnv(unsetList=["HELLO"])
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('scope', 'workspace'),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.wm.getFullEnvironment(profile).toList())

        profile.updateEnv(setMap=OrderedDict(
            (("scope", "profile"), ("HELLO", "world"))))
        profile = self.wm.updateProfile(profile)
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('scope', 'workspace'),
            ('scope', 'profile'),
            ('HELLO', 'world'),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.wm.getFullEnvironment(profile).toList())

        profile.updateEnv(unsetList=["HELLO"])
        profile = self.wm.updateProfile(profile)
        self.assertEqual([
            ("LEAF_VERSION", leaf.__version__),
            ("LEAF_PLATFORM_SYSTEM", platform.system()),
            ("LEAF_PLATFORM_MACHINE", platform.machine()),
            ("LEAF_PLATFORM_RELEASE", platform.release()),
            ("LEAF_NON_INTERACTIVE", "1"),
            ('scope', 'user'),
            ('LEAF_WORKSPACE', str(self.getWorkspaceFolder())),
            ('scope', 'workspace'),
            ('scope', 'profile'),
            ('LEAF_PROFILE', 'myenv'),
            ('LEAF_ENV_B', 'BAR'),
            ('LEAF_PATH_B', '$PATH:%s/env-B_1.0' % self.getInstallFolder()),
            ('LEAF_ENV_A', 'FOO'),
            ('LEAF_PATH_A', '$PATH:%s/env-A_1.0:%s/env-B_1.0' %
             (self.getInstallFolder(), self.getInstallFolder()))],
            self.wm.getFullEnvironment(profile).toList())

    def testPackageOverride(self):
        self.wm.initializeWorkspace()
        profile = self.wm.createProfile("myprofile")
        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        profile = self.wm.updateProfile(profile)
        self.wm.provisionProfile(profile)

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
        profile = self.wm.updateProfile(profile)
        self.wm.provisionProfile(profile)

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
        self.assertEqual(
            PackageIdentifier.fromStringList(["container-E_1.1",
                                              "container-B_1.0",
                                              "container-C_1.0",
                                              "container-A_1.0"]),
            list(map(Manifest.getIdentifier,
                     self.wm.getProfileDependencies(profile))))

    def testFeatures(self):
        fm = FeatureManager(self.wm)

        feature = fm.getFeature("myFeatureFoo")
        self.assertIsNotNone(feature)

        self.assertEqual("FOO",
                         feature.getKey())
        self.assertEqual({"bar": "BAR",
                          "notbar": "OTHER_VALUE"},
                         feature.getValues())

        self.assertEqual(None,
                         self.wm.getUserEnvironment().findValue("FOO"))
        fm.toggleUserFeature("myFeatureFoo", "bar", self.wm)
        self.assertEqual("BAR",
                         self.wm.getUserEnvironment().findValue("FOO"))

        self.wm.initializeWorkspace()
        self.assertEqual(None,
                         self.wm.getWorkspaceEnvironment().findValue("FOO"))
        fm.toggleWorkspaceFeature("myFeatureFoo", "bar", self.wm)
        self.assertEqual("BAR",
                         self.wm.getWorkspaceEnvironment().findValue("FOO"))

        profile = self.wm.createProfile("myprofile")
        self.wm.switchProfile(profile)
        self.assertEqual(None,
                         self.wm.getProfile("myprofile").getEnvironment().findValue("FOO"))
        fm.toggleProfileFeature("myFeatureFoo", "bar", self.wm)
        self.assertEqual("BAR",
                         self.wm.getProfile("myprofile").getEnvironment().findValue("FOO"))

        with self.assertRaises(ValueError):
            fm.toggleUserFeature("unknwonFeature", "unknownValue", self.wm)

        with self.assertRaises(ValueError):
            fm.toggleUserFeature("myFeatureFoo", "unknownValue", self.wm)

        # Error cases
        fm.toggleUserFeature("featureWithDups", "enum1", self.wm)
        with self.assertRaises(ValueError):
            fm.toggleUserFeature("featureWithDups", "enum2", self.wm)
        with self.assertRaises(ValueError):
            fm.toggleUserFeature("featureWithMultipleKeys", "enum1", self.wm)

    def testResolveLatest(self):
        self.assertEqual(2, len(self.wm.listRemotes(True)))
        remote2 = self.wm.listRemotes()["other"]
        remote2.setEnabled(False)
        self.wm.updateRemote(remote2)
        self.assertEqual(1, len(self.wm.listRemotes(True)))

        self.wm.initializeWorkspace()
        profile = self.wm.createProfile("myprofile")
        profile.addPackages(
            PackageIdentifier.fromStringList(["testlatest_1.0"]))
        profile = self.wm.updateProfile(profile)
        self.wm.provisionProfile(profile)
        self.checkInstalledPackages(["testlatest_1.0",
                                     "version_1.1"])
        self.checkProfileContent("myprofile",
                                 ["testlatest",
                                  "version"])

        remote2 = self.wm.listRemotes()["other"]
        remote2.setEnabled(True)
        self.wm.updateRemote(remote2)
        self.assertEqual(2, len(self.wm.listRemotes(True)))
        self.wm.fetchRemotes()

        self.wm.provisionProfile(profile)
        self.checkInstalledPackages(["testlatest_1.0",
                                     "version_1.1",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["testlatest",
                                  "version"])
