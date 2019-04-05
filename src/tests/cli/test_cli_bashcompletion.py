"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import subprocess

from leaf.core.constants import LeafSettings
from leaf.model.package import PackageIdentifier
from tests.testutils import TEST_RESOURCES_FOLDER, LeafTestCaseWithCli, LEAF_SYSTEM_ROOT

COMPLETION_SCRIPT = TEST_RESOURCES_FOLDER / "leaf-completion-test.sh"


def get_completion_list(cmd):
    command = [str(COMPLETION_SCRIPT)]
    if cmd.endswith("..."):
        command.append("--partial")
        cmd = cmd[:-3]
    command += cmd.split(" ")
    stdout, _stderr = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    out = stdout.decode().splitlines()
    return out


CONDITION_PACKAGES = [
    "condition_1.0",
    "condition-A_1.0",
    "condition-A_2.0",
    "condition-B_1.0",
    "condition-C_1.0",
    "condition-D_1.0",
    "condition-E_1.0",
    "condition-F_1.0",
    "condition-G_1.0",
    "condition-H_1.0",
]


class TestCliBashCompletion(LeafTestCaseWithCli):
    def setUp(self):
        super().setUp()
        self.leaf_exec(("remote", "fetch"))

    def test_package_install(self):
        completions = get_completion_list("package install")
        self.assertLess(30, len(completions))
        for pis in completions:
            self.assertTrue(PackageIdentifier.is_valid_identifier(pis))

        self.assertEqual(get_completion_list("package install condition..."), CONDITION_PACKAGES)

    def test_search(self):
        self.leaf_exec(("remote", "enable"), "other")

        completions = get_completion_list("search")
        self.assertLess(30, len(completions))
        for pis in completions:
            self.assertTrue(PackageIdentifier.is_valid_identifier(pis))

        self.assertEqual(get_completion_list("search dition..."), CONDITION_PACKAGES)

    def test_dash_p(self):
        for v in ("setup", "profile config"):
            for a in ("-p", "--add-package"):
                cmd = "{verb} {arg} condition...".format(verb=v, arg=a)
                self.assertEqual(get_completion_list(cmd), CONDITION_PACKAGES, cmd)

    def test_package_uninstall(self):
        self.leaf_exec(("package", "install"), "condition_1.0")

        self.assertEqual(
            get_completion_list("package uninstall"), ["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )

    def test_package_sync(self):
        self.leaf_exec(("package", "install"), "condition_1.0")

        self.assertEqual(get_completion_list("package sync"), ["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])

    def test_remote(self):
        for v in ("enable", "disable", "remove"):
            self.assertEqual(get_completion_list("remote {verb}".format(verb=v)), ["default", "other"])
            self.assertEqual(get_completion_list("remote {verb} def...".format(verb=v)), ["default"])

    def test_profile(self):
        self.leaf_exec("init")
        self.leaf_exec("profile", "create", "foo")
        self.leaf_exec("profile", "create", "profile1")
        self.leaf_exec("profile", "create", "profile2")
        for v in ("select", "profile rename", "profile delete", "profile switch", "profile config", "profile sync"):
            self.assertEqual(get_completion_list(v), ["foo", "profile1", "profile2"])
            self.assertEqual(get_completion_list("{verb} pro...".format(verb=v)), ["profile1", "profile2"])

    def test_env_unset(self):
        self.leaf_exec("env", "user", "--set", "FOO1=BAR")
        self.leaf_exec("env", "user", "--set", "FOO2=BAR")
        self.leaf_exec("env", "user", "--set", "PLOP=BAR")

        self.assertEqual(get_completion_list("env user --unset"), ["FOO1", "FOO2", "PLOP"])
        self.assertEqual(get_completion_list("env user --unset F..."), ["FOO1", "FOO2"])

    def test_settings(self):
        self.leaf_exec(("package", "install"), "settings_1.0")
        for v in ("set", "reset", "get"):
            self.assertEqual(
                get_completion_list("config {verb} settings...".format(verb=v)),
                ["settings.user", "settings.workspace", "settings.workspace-profile", "settings.lowercase", "settings.enum", "settings.foo"],
            )

    def test_help(self):

        LeafSettings.SYSTEM_PKG_FOLDERS.value = LEAF_SYSTEM_ROOT
        self.assertEqual(
            get_completion_list("help"),
            [
                "build",
                "colors",
                "config",
                "env",
                "feature",
                "getsrc",
                "init",
                "manifest",
                "package",
                "profile",
                "remote",
                "run",
                "search",
                "select",
                "setup",
                "shell",
                "status",
                "update",
            ],
        )

    def test_run(self):
        self.leaf_exec(("package", "install"), "scripts_1.0")

        self.assertEqual(get_completion_list("run"), ["echo", "env", "mytouch", "mytouch2", "mybin", "foo", "foo-noshell", "touch", "mytouch"])
        self.assertEqual(get_completion_list("run fo..."), ["foo", "foo-noshell"])

    def test_argcomplete(self):
        self.assertEqual(get_completion_list("p..."), ["profile", "package"])
