'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''


import subprocess
import unittest

from leaf.model.package import PackageIdentifier
from tests.testutils import RESOURCE_FOLDER, LeafTestCaseWithCli

COMPLETION_SCRIPT = RESOURCE_FOLDER / 'leaf-completion-test.sh'


def getCompletionList(cmd):
    command = [str(COMPLETION_SCRIPT)]
    if cmd.endswith("..."):
        command.append("--partial")
        cmd = cmd[:-3]
    command += cmd.split(' ')
    stdout, _stderr = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    out = stdout.decode().splitlines()
    return out


CONDITION_PACKAGES = ["condition_1.0",
                      "condition-A_1.0",
                      "condition-A_2.0",
                      "condition-B_1.0",
                      "condition-C_1.0",
                      "condition-D_1.0",
                      "condition-E_1.0",
                      "condition-F_1.0",
                      "condition-G_1.0",
                      "condition-H_1.0"]


class TestCliBashCompletion(LeafTestCaseWithCli):

    def setUp(self):
        super().setUp()
        self.leafExec(('remote', 'fetch'))

    def testPackageInstall(self):
        completions = getCompletionList("package install")
        self.assertLess(30, len(completions))
        for pis in completions:
            self.assertTrue(PackageIdentifier.isValidIdentifier(pis))

        self.assertEqual(
            getCompletionList("package install condition..."),
            CONDITION_PACKAGES)

    def testSearch(self):
        self.leafExec(("remote", "enable"), "other")

        completions = getCompletionList("search")
        self.assertLess(30, len(completions))
        for pis in completions:
            self.assertTrue(PackageIdentifier.isValidIdentifier(pis))

        self.assertEqual(
            getCompletionList("search dition..."),
            CONDITION_PACKAGES)

    def testDashP(self):
        for v in ('setup', 'profile config'):
            for a in ('-p', '--add-package'):
                cmd = "%s %s condition..." % (v, a)
                self.assertEqual(getCompletionList(cmd),
                                 CONDITION_PACKAGES, cmd)

    def testPackageUninstall(self):
        self.leafExec(("package", "install"), "condition_1.0")

        self.assertEqual(
            getCompletionList("package uninstall"),
            ['condition_1.0',
             'condition-B_1.0',
             'condition-D_1.0',
             'condition-F_1.0',
             'condition-H_1.0'])

    def testPackageSync(self):
        self.leafExec(("package", "install"), "condition_1.0")

        self.assertEqual(
            getCompletionList("package sync"),
            ['condition_1.0',
             'condition-B_1.0',
             'condition-D_1.0',
             'condition-F_1.0',
             'condition-H_1.0'])

    def testRemote(self):
        for v in ('enable', 'disable', 'remove'):
            self.assertEqual(
                getCompletionList("remote %s" % v),
                ["default",
                 "other"])
            self.assertEqual(
                getCompletionList("remote %s def..." % v),
                ["default"])

    def testProfile(self):
        self.leafExec("init")
        self.leafExec("profile", "create", "foo")
        self.leafExec("profile", "create", "profile1")
        self.leafExec("profile", "create", "profile2")
        for v in ('select',
                  'profile rename',
                  'profile delete',
                  'profile switch',
                  'profile config',
                  'profile sync'):
            self.assertEqual(
                getCompletionList("%s" % v),
                ["foo",
                 "profile1",
                 "profile2"])
            self.assertEqual(
                getCompletionList("%s pro..." % v),
                ["profile1",
                 "profile2"])

    def testEnvUnset(self):
        self.leafExec("env", "user", "--set", "FOO1=BAR")
        self.leafExec("env", "user", "--set", "FOO2=BAR")
        self.leafExec("env", "user", "--set", "PLOP=BAR")

        self.assertEqual(
            getCompletionList("env user --unset"),
            ["FOO1",
             "FOO2",
             "PLOP"])
        self.assertEqual(
            getCompletionList("env user --unset F..."),
            ["FOO1",
             "FOO2"])

    def testFeature(self):
        for v in ('toggle', 'query'):
            self.assertEqual(
                getCompletionList("feature %s" % v),
                ["featureWithDups",
                 "featureWithMultipleKeys",
                 "myFeatureFoo",
                 "myFeatureHello",
                 "test-src"])
            self.assertEqual(
                getCompletionList("feature %s my..." % v),
                ["myFeatureFoo",
                 "myFeatureHello"])

        self.assertEqual(
            getCompletionList("feature toggle myFeatureHello"),
            ["default",
             "world"])

    def testHelp(self):
        self.assertEqual(
            getCompletionList("help"),
            ['build',
             'colors',
             'config',
             'env',
             'feature',
             'getsrc',
             'init',
             'manifest',
             'package',
             'profile',
             'remote',
             'run',
             'search',
             'select',
             'setup',
             'shell',
             'status',
             'update'])

    @unittest.skip
    def testGetsrc(self):
        self.assertEqual(
            getCompletionList("getsrc"),
            ['test'])

    def testRun(self):
        self.leafExec(('package', 'install'), 'scripts_1.0')

        self.assertEqual(
            getCompletionList("run"),
            ['echo',
             'env',
             'mytouch',
             'mytouch2',
             'mybin',
             'foo',
             'foo-noshell',
             'touch',
             'mytouch'])
        self.assertEqual(
            getCompletionList("run fo..."),
            ['foo',
             'foo-noshell'])
        pass

    def testArgcomplete(self):
        self.assertEqual(
            getCompletionList("p..."),
            ["profile",
             "package"])
