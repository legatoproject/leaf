"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os
import shutil

from leaf.core.constants import LeafFiles
from tests.testutils import LeafTestCaseWithCli, env_file_to_map, get_lines


class TestCliWorkspaceManager(LeafTestCaseWithCli):
    def test_init_without_profile(self):
        self.leaf_exec("init")
        self.leaf_exec("status")
        self.leaf_exec(("env", "profile"), expected_rc=2)
        self.leaf_exec(("env", "print"), expected_rc=2)

    def test_create_profile(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A_1.0")
        self.check_profile_content("foo", [])
        self.leaf_exec(("profile", "sync"))
        self.check_profile_content("foo", ["container-A", "container-B", "container-C", "container-E"])
        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR")
        self.leaf_exec("status")
        self.leaf_exec(("profile", "sync"))
        self.leaf_exec(("env", "print"))

    def test_profile_multi_delete(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "A")
        self.check_profile_content("A", [])
        self.leaf_exec(("profile", "create"), "B")
        self.check_profile_content("B", [])
        self.leaf_exec(("profile", "create"), "C")
        self.check_profile_content("C", [])
        self.leaf_exec(("profile", "create"), "D")
        self.check_profile_content("D", [])

        self.leaf_exec(("profile", "list"), "A", "B", "C")

        self.leaf_exec(("profile", "delete"), "A", "B", "C", "D")
        self.check_profile_content("A", None)
        self.check_profile_content("B", None)
        self.check_profile_content("C", None)
        self.check_profile_content("D", None)

    def test_workspace_not_init(self):
        self.leaf_exec(("profile", "sync"), expected_rc=2)
        self.leaf_exec("status")

    def test_configure_packages(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A_1.0", "--add-package", "install_1.0")
        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR", "--set", "FOO2=BAR2")
        self.check_profile_content("foo", [])
        self.leaf_exec(("profile", "sync"))
        self.check_profile_content("foo", ["container-A", "container-B", "container-C", "container-E", "install"])

        self.leaf_exec(("profile", "create"), "foo", expected_rc=2)

    def test_delete(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.check_profile_content("foo", [])
        self.leaf_exec(("profile", "create"), "foo2")
        self.check_profile_content("foo2", [])
        self.leaf_exec("status")
        self.leaf_exec(("profile", "delete"), "foo2")
        self.check_profile_content("foo", [])
        self.check_profile_content("foo2", None)
        self.leaf_exec("status")

    def test_reserved_name(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "current", expected_rc=2)
        self.leaf_exec(("profile", "create"), "", expected_rc=2)
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "create"), "foo", expected_rc=2)

    def test_auto_find_workspace(self):
        pf_config_file = self.ws_folder / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(pf_config_file.exists())

        self.leaf_exec("init")
        self.assertTrue(pf_config_file.exists())
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec("select", "foo")

        self.leaf_exec("status")
        self.leaf_exec("select", "foo", alt_ws=self.alt_ws_folder, expected_rc=2)

        subfolder = self.ws_folder / "foo" / "bar"
        subfolder.mkdir(parents=True)
        self.leaf_exec("select", "foo", alt_ws=subfolder, expected_rc=2)

        oldpwd = os.getcwd()
        try:
            os.chdir(str(subfolder))
            self.leaf_exec("select", "foo")
        finally:
            os.chdir(oldpwd)

    def test_without_version(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A")
        self.leaf_exec("status")
        self.leaf_exec(("profile", "sync"))
        self.leaf_exec("status")
        self.check_profile_content("foo", ["container-A", "container-C", "container-D"])

    def test_bootstrap_workspace(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A")
        self.leaf_exec(("profile", "sync"))
        self.check_current_profile("foo")
        self.leaf_exec(("profile", "create"), "bar")
        self.check_current_profile("bar")
        self.leaf_exec("status")
        self.leaf_exec(("env", "print"))
        self.check_profile_content("foo", ["container-A", "container-C", "container-D"])
        data_folder = self.ws_folder / LeafFiles.WS_DATA_FOLDERNAME
        self.assertTrue(data_folder.exists())
        shutil.rmtree(str(data_folder))
        self.assertFalse(data_folder.exists())

        self.leaf_exec("status")
        self.leaf_exec(("env", "print"), expected_rc=2)
        self.leaf_exec(("profile", "switch"), "foo")
        self.check_current_profile("foo")
        self.leaf_exec(("env", "print"), expected_rc=2)
        self.leaf_exec(("profile", "sync"))
        self.leaf_exec(("env", "print"))
        self.check_profile_content("foo", ["container-A", "container-C", "container-D"])

    def test_rename_profile(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A")
        self.leaf_exec(("profile", "sync"))
        self.leaf_exec(("env", "print"))

        self.leaf_exec(("profile", "rename"), "bar")
        self.leaf_exec(("env", "profile"))
        self.leaf_exec(("env", "profile"), "bar")
        self.leaf_exec(("env", "profile"), "foo", expected_rc=2)

        self.leaf_exec(("profile", "rename"), "foo")
        self.leaf_exec(("env", "profile"))
        self.leaf_exec(("env", "profile"), "foo")

    def test_env(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "ENV-A")
        self.leaf_exec(("profile", "config"), "-p", "env-A")
        self.leaf_exec(("profile", "sync"))
        self.leaf_exec(("env", "profile"), "ENV-A")
        self.leaf_exec(("env", "profile"))
        self.leaf_exec(
            ("env", "profile"),
            "--activate-script",
            str(self.ws_folder / "in.env"),
            "--deactivate-script",
            str(self.ws_folder / "out.env"),
        )
        self.assertTrue((self.ws_folder / "in.env").exists())
        self.assertTrue((self.ws_folder / "out.env").exists())

    def test_conditional_install_user(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p" "condition")

        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])
        self.check_profile_content("foo", ["condition-B", "condition-D", "condition-F", "condition-H", "condition"])

        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec(("env", "profile"), "--set", "HELLO=PLOP")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec(("env", "profile"), "--set", "FOO2=BAR2", "--set", "HELLO=wOrlD")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            [
                "condition_1.0",
                "condition-A_1.0",
                "condition-B_1.0",
                "condition-C_1.0",
                "condition-D_1.0",
                "condition-E_1.0",
                "condition-F_1.0",
                "condition-G_1.0",
                "condition-H_1.0",
            ]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-E", "condition-G", "condition"])

    def test_conditional_install_ws(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p" "condition")

        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])
        self.check_profile_content("foo", ["condition-B", "condition-D", "condition-F", "condition-H", "condition"])

        self.leaf_exec(("env", "workspace"), "--set", "FOO=BAR")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec(("env", "workspace"), "--set", "HELLO=PLOP")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec(("env", "workspace"), "--set", "FOO2=BAR2", "--set", "HELLO=wOrlD")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            [
                "condition_1.0",
                "condition-A_1.0",
                "condition-B_1.0",
                "condition-C_1.0",
                "condition-D_1.0",
                "condition-E_1.0",
                "condition-F_1.0",
                "condition-G_1.0",
                "condition-H_1.0",
            ]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-E", "condition-G", "condition"])

    def test_conditional_install_pf(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p" "condition")

        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])
        self.check_profile_content("foo", ["condition-B", "condition-D", "condition-F", "condition-H", "condition"])

        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec(("env", "profile"), "--set", "HELLO=PLOP")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec(("env", "profile"), "--set", "FOO2=BAR2", "--set", "HELLO=wOrlD")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            [
                "condition_1.0",
                "condition-A_1.0",
                "condition-B_1.0",
                "condition-C_1.0",
                "condition-D_1.0",
                "condition-E_1.0",
                "condition-F_1.0",
                "condition-G_1.0",
                "condition-H_1.0",
            ]
        )
        self.check_profile_content("foo", ["condition-A", "condition-C", "condition-E", "condition-G", "condition"])

    def test_env_set_unset_gen_scripts(self):

        self.leaf_exec(("env", "user"))
        self.leaf_exec(("env", "workspace"), expected_rc=2)
        self.leaf_exec(("env", "profile"), expected_rc=2)
        self.leaf_exec("init")
        self.leaf_exec(("env", "user"))
        self.leaf_exec(("env", "workspace"))
        self.leaf_exec(("env", "profile"), expected_rc=2)
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("env", "user"))
        self.leaf_exec(("env", "workspace"))
        self.leaf_exec(("env", "profile"))

        for scope in ["user", "workspace", "profile"]:
            verb = ("env", scope)
            self.leaf_exec(verb, "--set", "FOO=BAR")
            self.leaf_exec(verb, "--set", "HELLO=World")
            self.leaf_exec(verb, "--unset", "HELLO")
            self.leaf_exec(verb, "--set", "FOO=bar")
            self.leaf_exec(verb)

        self.leaf_exec(("env", "profile"), "--set FOO=BAR", expected_rc=2)
        self.leaf_exec(("env", "profile"))
        in_script = self.ws_folder / "in.env"
        out_script = self.ws_folder / "out.env"
        self.leaf_exec(("env", "print"), "--activate-script", in_script, "--deactivate-script", out_script)
        self.assertTrue(in_script.exists())
        self.assertTrue(out_script.exists())

        with open(str(in_script)) as fp:
            foo_count = 0
            for line in fp.read().splitlines():
                if line == 'export FOO="bar";':
                    foo_count += 1
            self.assertEqual(3, foo_count)

        with open(str(out_script)) as fp:
            foo_count = 0
            for line in fp.read().splitlines():
                if line == "unset FOO;":
                    foo_count += 1
            self.assertEqual(1, foo_count)

    def test_install_from_workspace(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "install_1.0")
        self.leaf_exec(("profile", "sync"))

        env_dump_file = self.install_folder / "install_1.0" / "dump.env"
        keys = [k for k in env_file_to_map(env_dump_file).keys() if k.startswith("LEAF_")]
        for key in [
            "LEAF_NON_INTERACTIVE",
            "LEAF_PLATFORM_MACHINE",
            "LEAF_PLATFORM_RELEASE",
            "LEAF_PLATFORM_SYSTEM",
            "LEAF_WORKSPACE",
            "LEAF_PROFILE",
            "LEAF_VERSION",
        ]:
            self.assertTrue(key in keys, msg=key)
        print(keys)

    def test_package_override(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "myprofile")
        self.leaf_exec(("profile", "config"), "-p", "container-A_1.0")
        self.leaf_exec(("profile", "sync"))

        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0"])
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E"])

        self.leaf_exec(("profile", "config"), "-p", "container-E_1.1")
        self.leaf_exec(("profile", "sync"))

        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0", "container-E_1.1"])
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E"])

    def test_overide_keep_depends(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "condition_1.0")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])
        self.check_profile_content("foo", ["condition", "condition-B", "condition-D", "condition-F", "condition-H"])

        self.leaf_exec(("profile", "config"), "-p", "condition-A_2.0")
        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR")
        self.leaf_exec(("profile", "sync"))
        self.check_installed_packages(
            [
                "condition_1.0",
                "condition-A_1.0",
                "condition-A_2.0",
                "condition-B_1.0",
                "condition-C_1.0",
                "condition-D_1.0",
                "condition-F_1.0",
                "condition-H_1.0",
            ]
        )
        self.check_profile_content("foo", ["condition", "condition-A", "condition-C", "condition-F"])

    def test_features(self):
        self.leaf_exec(("feature", "list"))
        self.leaf_exec(("feature", "query"), "featureWithDups")
        self.leaf_exec(("feature", "toggle"), "--user", "featureWithDups", "enum1")
        self.leaf_exec(("feature", "toggle"), "--workspace", "featureWithDups", "enum1", expected_rc=2)
        self.leaf_exec(("feature", "toggle"), "--profile", "featureWithDups", "enum1", expected_rc=2)

        self.leaf_exec(("init"))
        self.leaf_exec(("feature", "toggle"), "--user", "featureWithDups", "enum1")
        self.leaf_exec(("feature", "toggle"), "--workspace", "featureWithDups", "enum1")
        self.leaf_exec(("feature", "toggle"), "--profile", "featureWithDups", "enum1", expected_rc=2)

        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("feature", "toggle"), "--user", "featureWithDups", "enum1")
        self.leaf_exec(("feature", "toggle"), "--workspace", "featureWithDups", "enum1")
        self.leaf_exec(("feature", "toggle"), "--profile", "featureWithDups", "enum1")

    def test_sync(self):
        sync_file = self.install_folder / "sync_1.0" / "sync.log"
        self.assertFalse(sync_file.exists())

        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "sync_1.0")
        self.leaf_exec(("profile", "sync"))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE"], get_lines(sync_file))

        self.leaf_exec(("profile", "sync"))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE"], get_lines(sync_file))

        self.leaf_exec(("package", "sync"), "sync_1.0")
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE", "MYVALUE"], get_lines(sync_file))

        self.leaf_exec(("env", "workspace"), "--set", "MYVAR2=AAA")
        self.leaf_exec(("profile", "sync"))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE", "MYVALUE", "MYVALUE AAA"], get_lines(sync_file))

        self.leaf_exec(("env", "profile"), "--set", "MYVAR2=BBB")
        self.leaf_exec(("profile", "sync"))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE", "MYVALUE", "MYVALUE AAA", "MYVALUE BBB"], get_lines(sync_file))

        self.leaf_exec(("env", "profile"), "--set", "MYVAR1=FOO")
        self.leaf_exec(("profile", "sync"))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE", "MYVALUE", "MYVALUE AAA", "MYVALUE BBB", "MYVALUE BBB"], get_lines(sync_file))


class TestCliWorkspaceManagerVerbose(TestCliWorkspaceManager):
    def __init__(self, *args, **kwargs):
        TestCliWorkspaceManager.__init__(self, *args, verbosity="verbose", **kwargs)


class TestCliWorkspaceManagerQuiet(TestCliWorkspaceManager):
    def __init__(self, *args, **kwargs):
        TestCliWorkspaceManager.__init__(self, *args, verbosity="quiet", **kwargs)
