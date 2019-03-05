"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import platform
from collections import OrderedDict

import leaf
from leaf.api import WorkspaceManager
from leaf.core.error import InvalidProfileNameException, LeafException, NoProfileSelected, ProfileNameAlreadyExistException
from leaf.model.features import FeatureManager
from leaf.model.package import IDENTIFIER_GETTER, PackageIdentifier
from tests.testutils import LeafTestCaseWithRepo


class TestApiWorkspaceManager(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()
        self.wm = WorkspaceManager(self.ws_folder)
        self.wm.set_install_folder(self.install_folder)
        self.wm.create_remote("default", self.remote_url1, insecure=True)
        self.wm.create_remote("other", self.remote_url2, insecure=True)

    def test_init(self):
        with self.assertRaises(Exception):
            self.wm.create_profile("foo")
        self.wm.init_ws()
        profile = self.wm.create_profile("foo")
        self.assertIsNotNone(profile)
        self.assertEqual("foo", profile.name)

    def test_add_delete_profile(self):
        self.wm.init_ws()
        self.wm.create_profile("foo")
        self.assertEqual(1, len(self.wm.list_profiles()))

        with self.assertRaises(Exception):
            self.wm.create_profile("foo")

        self.wm.create_profile("bar")
        self.assertEqual(2, len(self.wm.list_profiles()))

        with self.assertRaises(Exception):
            self.wm.create_profile("bar")

        self.wm.delete_profile("foo")
        self.assertEqual(1, len(self.wm.list_profiles()))

        with self.assertRaises(Exception):
            self.wm.delete_profile("foo")
        self.assertEqual(1, len(self.wm.list_profiles()))

    def test_updatet_profile(self):
        self.wm.init_ws()
        profile = self.wm.create_profile("foo")
        self.assertEqual([], profile.packages)
        self.assertEqual(OrderedDict(), profile._getenvmap())

        profile.add_packages(PackageIdentifier.parse_list(["container-A_1.0"]))
        profile.update_environment(OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]))
        self.wm.update_profile(profile)

        self.assertEqual(["container-A_1.0"], profile.packages)
        self.assertEqual(OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]), profile._getenvmap())

        profile.add_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        self.wm.update_profile(profile)
        self.assertEqual(["container-A_2.1"], profile.packages)

        profile.add_packages(PackageIdentifier.parse_list(["env-A_1.0"]))
        self.wm.update_profile(profile)
        self.assertEqual(["container-A_2.1", "env-A_1.0"], profile.packages)

        profile.remove_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        self.wm.update_profile(profile)
        self.assertEqual(["env-A_1.0"], profile.packages)

        with self.assertRaises(Exception):
            profile.name = "fooooooo"
            self.wm.update_profile(profile)

    def test_rename_profile(self):
        self.wm.init_ws()
        self.wm.create_profile("foo")

        with self.assertRaises(NoProfileSelected):
            self.wm.current_profile_name
        profile = self.wm.get_profile("foo")
        self.wm.switch_profile(profile)
        self.assertEqual("foo", self.wm.current_profile_name)

        profile.add_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        profile.update_environment({"FOO": "BAR"})
        self.wm.update_profile(profile)

        self.wm.provision_profile(profile)
        self.assertEqual("foo", self.wm.current_profile_name)

        self.check_profile_content("foo", ["container-A", "container-C", "container-D"])

        profile = self.wm.rename_profile("foo", "bar")
        self.assertEqual(1, len(self.wm.list_profiles()))
        self.assertEqual("bar", profile.name)
        self.assertEqual("bar", self.wm.get_profile("bar").name)
        self.assertEqual("bar", self.wm.current_profile_name)
        self.check_profile_content("bar", ["container-A", "container-C", "container-D"])
        self.wm.build_full_environment(profile)
        with self.assertRaises(ProfileNameAlreadyExistException):
            self.wm.rename_profile("bar", "bar")
        with self.assertRaises(InvalidProfileNameException):
            self.wm.rename_profile("foo", "bar")

    def test_switch_profile(self):
        self.wm.init_ws()
        profile = self.wm.create_profile("foo")
        self.wm.switch_profile(profile)
        self.assertEqual("foo", self.wm.current_profile_name)

        profile2 = self.wm.create_profile("bar")
        self.wm.switch_profile(profile2)
        self.assertEqual("bar", self.wm.current_profile_name)

    def test_env(self):
        self.wm.init_ws()
        profile = self.wm.create_profile("myenv")
        profile.add_packages([PackageIdentifier.parse(pis) for pis in ["env-A_1.0", "env-A_1.0"]])
        self.wm.update_profile(profile)

        self.wm.switch_profile(profile)
        self.wm.provision_profile(profile)

        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("LEAF_PROFILE", "myenv"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

        self.wm.update_user_environment(set_map=OrderedDict((("scope", "user"), ("HELLO", "world"))))
        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("scope", "user"),
                ("HELLO", "world"),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("LEAF_PROFILE", "myenv"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

        self.wm.update_user_environment(unset_list=["HELLO"])
        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("scope", "user"),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("LEAF_PROFILE", "myenv"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

        self.wm.update_ws_environment(set_map=OrderedDict((("scope", "workspace"), ("HELLO", "world"))))
        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("scope", "user"),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("scope", "workspace"),
                ("HELLO", "world"),
                ("LEAF_PROFILE", "myenv"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

        self.wm.update_ws_environment(unset_list=["HELLO"])
        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("scope", "user"),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("scope", "workspace"),
                ("LEAF_PROFILE", "myenv"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

        profile.update_environment(set_map=OrderedDict((("scope", "profile"), ("HELLO", "world"))))
        self.wm.update_profile(profile)
        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("scope", "user"),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("scope", "workspace"),
                ("LEAF_PROFILE", "myenv"),
                ("scope", "profile"),
                ("HELLO", "world"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

        profile.update_environment(unset_list=["HELLO"])
        self.wm.update_profile(profile)
        self.assertEqual(
            [
                ("LEAF_VERSION", leaf.__version__),
                ("LEAF_PLATFORM_SYSTEM", platform.system()),
                ("LEAF_PLATFORM_MACHINE", platform.machine()),
                ("LEAF_PLATFORM_RELEASE", platform.release()),
                ("scope", "user"),
                ("LEAF_WORKSPACE", str(self.ws_folder)),
                ("scope", "workspace"),
                ("LEAF_PROFILE", "myenv"),
                ("scope", "profile"),
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            self.wm.build_full_environment(profile).tolist(),
        )

    def test_package_override(self):
        self.wm.init_ws()
        profile = self.wm.create_profile("myprofile")
        profile.add_packages(PackageIdentifier.parse_list(["container-A_1.0"]))
        self.wm.update_profile(profile)
        self.wm.provision_profile(profile)

        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0"])
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E"])

        profile.add_packages(PackageIdentifier.parse_list(["container-E_1.1"]))
        self.wm.update_profile(profile)
        self.wm.provision_profile(profile)

        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0", "container-E_1.1"])
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E"])
        self.assertEqual(
            PackageIdentifier.parse_list(["container-E_1.1", "container-B_1.0", "container-C_1.0", "container-A_1.0"]),
            list(map(IDENTIFIER_GETTER, self.wm.get_profile_dependencies(profile))),
        )

    def test_features(self):
        fm = FeatureManager()
        fm.append_features(self.wm.list_available_packages().values())

        feature = fm.get_feature("myFeatureFoo")
        self.assertIsNotNone(feature)

        self.assertEqual("FOO", feature.key)
        self.assertEqual({"bar": "BAR", "notbar": "OTHER_VALUE"}, feature.values)

        self.assertEqual(None, self.wm.build_user_environment().find_value("FOO"))

        # Toggle user feature
        usrc = self.wm.read_user_configuration()
        fm.toggle_feature("myFeatureFoo", "bar", usrc)
        self.wm.write_user_configuration(usrc)

        self.assertEqual("BAR", self.wm.build_user_environment().find_value("FOO"))

        self.wm.init_ws()
        self.assertEqual(None, self.wm.build_ws_environment().find_value("FOO"))

        # Toggle ws feature
        wsrc = self.wm.read_ws_configuration()
        fm.toggle_feature("myFeatureFoo", "bar", wsrc)
        self.wm.write_ws_configuration(wsrc)

        self.assertEqual("BAR", self.wm.build_ws_environment().find_value("FOO"))

        profile = self.wm.create_profile("myprofile")
        self.wm.switch_profile(profile)
        self.assertEqual(None, self.wm.get_profile("myprofile").build_environment().find_value("FOO"))

        # Toggle profile feature
        fm.toggle_feature("myFeatureFoo", "bar", profile)
        self.wm.update_profile(profile)

        self.assertEqual("BAR", self.wm.get_profile("myprofile").build_environment().find_value("FOO"))

        with self.assertRaises(LeafException):
            usrc = self.wm.read_user_configuration()
            fm.toggle_feature("unknwonFeature", "unknownValue", usrc)

        with self.assertRaises(LeafException):
            usrc = self.wm.read_user_configuration()
            fm.toggle_feature("myFeatureFoo", "unknownValue", usrc)

        # Error cases
        wsrc = self.wm.read_ws_configuration()
        fm.toggle_feature("featureWithDups", "enum1", wsrc)
        self.wm.write_ws_configuration(wsrc)
        with self.assertRaises(LeafException):
            usrc = self.wm.read_user_configuration()
            fm.toggle_feature("featureWithDups", "enum2", usrc)
        with self.assertRaises(LeafException):
            usrc = self.wm.read_user_configuration()
            fm.toggle_feature("featureWithMultipleKeys", "enum1", usrc)

    def test_resolve_latest(self):
        self.assertEqual(2, len(self.wm.list_remotes(True)))
        remote2 = self.wm.list_remotes()["other"]
        remote2.enabled = False
        self.wm.update_remote(remote2)
        self.assertEqual(1, len(self.wm.list_remotes(True)))

        self.wm.init_ws()
        profile = self.wm.create_profile("myprofile")
        profile.add_packages(PackageIdentifier.parse_list(["testlatest_1.0"]))
        self.wm.update_profile(profile)
        self.wm.provision_profile(profile)
        self.check_installed_packages(["testlatest_1.0", "version_1.1"])
        self.check_profile_content("myprofile", ["testlatest", "version"])

        remote2 = self.wm.list_remotes()["other"]
        remote2.enabled = True
        self.wm.update_remote(remote2)
        self.assertEqual(2, len(self.wm.list_remotes(True)))
        self.wm.fetch_remotes()

        self.wm.provision_profile(profile)
        self.check_installed_packages(["testlatest_1.0", "version_1.1", "version_2.0"])
        self.check_profile_content("myprofile", ["testlatest", "version"])

    def test_sync_with_package_not_available(self):
        self.wm.init_ws()

        self.assertEqual(len(self.wm.list_remotes(only_enabled=True)), 2)
        self.assertTrue(PackageIdentifier.parse("container-A_1.0") in self.wm.list_available_packages())

        profile = self.wm.create_profile("myprofile")
        profile.add_packages(PackageIdentifier.parse_list(["container-A_1.0"]))
        self.wm.update_profile(profile)
        self.wm.provision_profile(profile)
        self.assertTrue(self.wm.is_profile_sync(profile))

        remote2 = self.wm.list_remotes()["default"]
        remote2.enabled = False
        self.wm.update_remote(remote2)
        self.assertEqual(len(self.wm.list_remotes(only_enabled=True)), 1)
        self.assertFalse(PackageIdentifier.parse("container-A_1.0") in self.wm.list_available_packages())

        profile = self.wm.create_profile("myprofile2")
        profile.add_packages(PackageIdentifier.parse_list(["container-A_1.0"]))
        self.wm.update_profile(profile)
        self.wm.provision_profile(profile)
        self.assertTrue(self.wm.is_profile_sync(profile))
