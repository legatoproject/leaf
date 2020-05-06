"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import platform
from collections import OrderedDict

import leaf
from leaf.api import WorkspaceManager
from leaf.core.constants import LeafSettings
from leaf.core.error import InvalidProfileNameException, LeafException, NoProfileSelected, ProfileNameAlreadyExistException
from leaf.model.base import Scope
from leaf.model.package import IDENTIFIER_GETTER, PackageIdentifier
from tests.testutils import LeafTestCaseWithRepo, env_tolist


class TestApiWorkspaceManager(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()
        self.wm = WorkspaceManager(self.workspace_folder)
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

        self.assertEqual(PackageIdentifier.parse_list(["container-A_1.0"]), profile.packages)
        self.assertEqual(OrderedDict([("FOO", "BAR"), ("FOO2", "BAR2")]), profile._getenvmap())

        profile.add_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        self.wm.update_profile(profile)
        self.assertEqual(PackageIdentifier.parse_list(["container-A_2.1"]), profile.packages)

        profile.add_packages(PackageIdentifier.parse_list(["env-A_1.0"]))
        self.wm.update_profile(profile)
        self.assertEqual(PackageIdentifier.parse_list(["container-A_2.1", "env-A_1.0"]), profile.packages)

        profile.remove_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        self.wm.update_profile(profile)
        self.assertEqual(PackageIdentifier.parse_list(["env-A_1.0"]), profile.packages)

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
        try:
            LeafSettings.PROFILE_NORELATIVE.value = 1

            self.wm.init_ws()
            profile = self.wm.create_profile("myenv")
            profile.add_packages([PackageIdentifier.parse(pis) for pis in ["env-A_1.0", "env-A_1.0"]])
            self.wm.update_profile(profile)

            self.wm.switch_profile(profile)
            self.wm.provision_profile(profile)

            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("LEAF_PROFILE", "myenv"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )

            self.wm.update_user_environment(set_map=OrderedDict((("scope", "user"), ("HELLO", "world"))))
            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("scope", "user"),
                    ("HELLO", "world"),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("LEAF_PROFILE", "myenv"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )

            self.wm.update_user_environment(unset_list=["HELLO"])
            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("scope", "user"),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("LEAF_PROFILE", "myenv"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )

            self.wm.update_ws_environment(set_map=OrderedDict((("scope", "workspace"), ("HELLO", "world"))))
            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("scope", "user"),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("scope", "workspace"),
                    ("HELLO", "world"),
                    ("LEAF_PROFILE", "myenv"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )

            self.wm.update_ws_environment(unset_list=["HELLO"])
            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("scope", "user"),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("scope", "workspace"),
                    ("LEAF_PROFILE", "myenv"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )

            profile.update_environment(set_map=OrderedDict((("scope", "profile"), ("HELLO", "world"))))
            self.wm.update_profile(profile)
            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("scope", "user"),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("scope", "workspace"),
                    ("LEAF_PROFILE", "myenv"),
                    ("scope", "profile"),
                    ("HELLO", "world"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )

            profile.update_environment(unset_list=["HELLO"])
            self.wm.update_profile(profile)
            self.assertEqual(
                [
                    ("LEAF_ENV_B", "BAR"),
                    ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_ENV_A", "FOO"),
                    ("LEAF_ENV_A2", "Hello"),
                    ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
                    ("LEAF_VERSION", leaf.__version__),
                    ("LEAF_PLATFORM_SYSTEM", platform.system()),
                    ("LEAF_PLATFORM_MACHINE", platform.machine()),
                    ("LEAF_PLATFORM_RELEASE", platform.release()),
                    ("scope", "user"),
                    ("LEAF_WORKSPACE", str(self.workspace_folder)),
                    ("scope", "workspace"),
                    ("LEAF_PROFILE", "myenv"),
                    ("scope", "profile"),
                ],
                env_tolist(self.wm.build_full_environment(profile)),
            )
        finally:
            LeafSettings.PROFILE_NORELATIVE.value = None

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

    def test_settings(self):
        self.wm.init_ws()
        profile = self.wm.create_profile("myprofile")
        self.wm.provision_profile(profile)
        self.wm.switch_profile(profile)

        self.wm.install_packages(PackageIdentifier.parse_list(["settings_1.0"]))

        setting = self.wm.get_setting("settings.lowercase")
        self.assertIsNotNone(setting)

        self.assertEqual(None, self.wm.get_setting_value("settings.lowercase"))
        with self.assertRaises(LeafException):
            self.wm.set_setting("settings.lowercase", "HELLO")
        with self.assertRaises(LeafException):
            self.wm.set_setting("settings.lowercase", "hello")
        self.wm.set_setting("settings.lowercase", "hello", Scope.USER)
        self.assertEqual("hello", self.wm.get_setting_value("settings.lowercase"))
        self.assertEqual("hello", self.wm.read_user_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))

        self.wm.set_setting("settings.lowercase", "helloo", Scope.WORKSPACE)
        self.assertEqual("helloo", self.wm.get_setting_value("settings.lowercase"))
        self.assertEqual("hello", self.wm.read_user_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))
        self.assertEqual("helloo", self.wm.read_ws_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))

        self.wm.set_setting("settings.lowercase", "hellooo", Scope.PROFILE)
        self.assertEqual("hellooo", self.wm.get_setting_value("settings.lowercase"))
        self.assertEqual("hello", self.wm.read_user_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))
        self.assertEqual("helloo", self.wm.read_ws_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))
        self.assertEqual("hellooo", self.wm.get_profile(self.wm.current_profile_name).build_environment().find_value("LEAF_SETTING_LOWERCASE"))

        self.wm.unset_setting("settings.lowercase")
        self.assertEqual(None, self.wm.get_setting_value("settings.lowercase"))
        self.assertEqual(None, self.wm.read_user_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))
        self.assertEqual(None, self.wm.read_ws_configuration().build_environment().find_value("LEAF_SETTING_LOWERCASE"))
        self.assertEqual(None, self.wm.get_profile(self.wm.current_profile_name).build_environment().find_value("LEAF_SETTING_LOWERCASE"))

        self.assertEqual(None, self.wm.get_setting_value("settings.user"))
        with self.assertRaises(LeafException):
            self.wm.set_setting("settings.user", "HELLO", Scope.WORKSPACE)
        with self.assertRaises(LeafException):
            self.wm.set_setting("settings.user", "HELLO", Scope.PROFILE)

        self.wm.set_setting("settings.user", "hello")
        self.assertEqual("hello", self.wm.get_setting_value("settings.user"))
        self.assertEqual("hello", self.wm.read_user_configuration().build_environment().find_value("LEAF_SETTING_USER"))

        self.wm.set_setting("settings.user", "hello2", Scope.USER)
        self.assertEqual("hello2", self.wm.get_setting_value("settings.user"))
        self.assertEqual("hello2", self.wm.read_user_configuration().build_environment().find_value("LEAF_SETTING_USER"))

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
