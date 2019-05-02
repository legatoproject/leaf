"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import subprocess

from leaf.core.constants import LeafSettings
from tests.testutils import LEAF_SYSTEM_ROOT, TEST_RESOURCES_FOLDER, LeafTestCaseWithCli

COMPLETION_SCRIPT = TEST_RESOURCES_FOLDER / "leaf-completion-test.sh"


def get_completion_list(cmd, sort=False):
    command = [str(COMPLETION_SCRIPT)]
    if cmd.endswith("..."):
        command.append("--partial")
        cmd = cmd[:-3]
    command += cmd.split(" ")
    stdout, _stderr = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    out = list(map(str.strip, stdout.decode().splitlines()))
    if sort:
        out = sorted(out)
    return out


CONDITION_PACKAGES = [
    "condition-A_1.0",
    "condition-A_2.0",
    "condition-B_1.0",
    "condition-C_1.0",
    "condition-D_1.0",
    "condition-E_1.0",
    "condition-F_1.0",
    "condition-G_1.0",
    "condition-H_1.0",
    "condition_1.0",
]


class TestCliBashCompletion(LeafTestCaseWithCli):
    def setUp(self):
        super().setUp()
        LeafSettings.SYSTEM_PKG_FOLDERS.value = LEAF_SYSTEM_ROOT
        self.leaf_exec(("remote", "fetch"))

    def test_package_install(self):
        self.assertLess(30, len(get_completion_list("package install")))
        self.assertEqual(get_completion_list("package install condition...", sort=True), CONDITION_PACKAGES)

    def test_search(self):
        self.leaf_exec(("remote", "enable"), "other")

        completions = get_completion_list("search")
        self.assertLess(30, len(completions))

        self.assertEqual(get_completion_list("search condition...", sort=True), CONDITION_PACKAGES)

    def test_dash_p(self):
        for verb in ("profile config", "setup", "update"):
            for arg in ("-p", "--add-package"):
                cmd = "{verb} {arg} condition...".format(verb=verb, arg=arg)
                self.assertEqual(get_completion_list(cmd, sort=True), CONDITION_PACKAGES, cmd)

    def test_package_uninstall(self):
        self.leaf_exec(("package", "install"), "condition_1.0")

        self.assertEqual(
            get_completion_list("package uninstall cond...", sort=True),
            ["condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"],
        )

    def test_package_sync(self):
        self.leaf_exec(("package", "install"), "condition_1.0")

        self.assertEqual(
            get_completion_list("package sync cond..."), ["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"]
        )

    def test_remote(self):
        for v in ("enable", "disable", "remove"):
            completions = get_completion_list("remote {verb}".format(verb=v))
            self.assertTrue("default" in completions)
            self.assertTrue("other" in completions)
            self.assertEqual(get_completion_list("remote {verb} def...".format(verb=v)), ["default"])

    def test_profile(self):
        self.leaf_exec("init")
        self.leaf_exec("profile", "create", "foo")
        self.leaf_exec("profile", "create", "profile1")
        self.leaf_exec("profile", "create", "profile2")
        for verb in ("select", "profile delete", "profile switch", "profile config", "profile sync"):
            completions = get_completion_list(verb)
            self.assertTrue("foo" in completions, verb)
            self.assertTrue("profile1" in completions, verb)
            self.assertTrue("profile2" in completions, verb)
            self.assertEqual(get_completion_list("{verb} pro...".format(verb=verb), sort=True), ["profile1", "profile2"])

    def test_env_unset(self):
        self.leaf_exec("env", "user", "--set", "FOO1=BAR")
        self.leaf_exec("env", "user", "--set", "FOO2=BAR")
        self.leaf_exec("env", "user", "--set", "PLOP=BAR")

        self.assertEqual(get_completion_list("env user --unset", sort=True), ["FOO1", "FOO2", "PLOP"])
        self.assertEqual(get_completion_list("env user --unset F...", sort=True), ["FOO1", "FOO2"])

    def test_settings(self):
        self.leaf_exec(("package", "install"), "settings_1.0")
        for v in ("set", "reset", "get"):
            self.assertEqual(
                get_completion_list("config {verb} settings...".format(verb=v)),
                ["settings.user", "settings.workspace", "settings.workspace-profile", "settings.lowercase", "settings.enum", "settings.foo"],
            )

    def test_run(self):
        self.leaf_exec(("package", "install"), "scripts_1.0")

        completions = get_completion_list("run")
        for word in ["echo", "env", "mytouch", "mytouch2", "mybin", "foo", "foo-noshell", "touch", "mytouch"]:
            self.assertTrue(word in completions)
        self.assertEqual(get_completion_list("run fo...", sort=True), ["foo", "foo-noshell"])

    def test_argcomplete(self):
        self.assertEqual(get_completion_list("p..."), ["profile", "package"])
