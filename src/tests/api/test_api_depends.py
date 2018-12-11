'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import unittest
from collections import OrderedDict
from unittest.case import TestCase

from leaf.constants import LeafFiles
from leaf.core.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import Manifest, PackageIdentifier
from tests.testutils import RESOURCE_FOLDER


def deps2strlist(deps):
    return list(map(str, map(Manifest.getIdentifier, deps)))


class TestApiDepends(unittest.TestCase):

    MANIFEST_MAP = {}

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        for f in RESOURCE_FOLDER.iterdir():
            manifestFile = f / LeafFiles.MANIFEST
            if manifestFile.exists():
                try:
                    mf = Manifest.parse(manifestFile)
                    TestApiDepends.MANIFEST_MAP[mf.getIdentifier()] = mf
                except Exception:
                    pass
        print("Found", len(TestApiDepends.MANIFEST_MAP), LeafFiles.MANIFEST)

    def testForInstall(self):
        availablePackages = TestApiDepends.MANIFEST_MAP
        installedPackages = {}
        deps = DependencyUtils.install(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            availablePackages,
            installedPackages,
            env=Environment())
        self.assertEqual(['container-E_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         deps2strlist(deps))

        pi = PackageIdentifier.fromString('container-E_1.0')
        installedPackages[pi] = TestApiDepends.MANIFEST_MAP.get(pi)

        deps = DependencyUtils.install(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            availablePackages,
            installedPackages,
            env=Environment())
        self.assertEqual(['container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         deps2strlist(deps))

    def testForUninstall(self):

        availablePackages = TestApiDepends.MANIFEST_MAP
        installedPackages = OrderedDict()

        for ap in DependencyUtils.install(
                PackageIdentifier.fromStringList(["container-A_1.0",
                                                  "container-A_2.0"]),
                availablePackages,
                installedPackages):
            installedPackages[ap.getIdentifier()] = ap

        self.assertEqual(['container-E_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         deps2strlist(installedPackages.values()))

        deps = DependencyUtils.uninstall(
            PackageIdentifier.fromStringList(["container-A_1.0"]),
            installedPackages)

        self.assertEqual(['container-A_1.0',
                          'container-B_1.0',
                          'container-E_1.0'],
                         deps2strlist(deps))

    def testConditionalInstall(self):
        availablePackages = TestApiDepends.MANIFEST_MAP
        installedPackages = {}

        def _getDeps(env):
            return DependencyUtils.install(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                availablePackages,
                installedPackages,
                env=env)

        env = Environment()
        deps = _getDeps(env)
        self.assertEqual(['condition-B_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2",
                                   "HELLO": "wOrlD"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-E_1.0',
                          'condition-G_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        pi = PackageIdentifier.fromString('condition-C_1.0')
        installedPackages[pi] = TestApiDepends.MANIFEST_MAP.get(pi)

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2",
                                   "HELLO": "wOrlD"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-E_1.0',
                          'condition-G_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

    def testConditionalTree(self):
        availablePackages = TestApiDepends.MANIFEST_MAP

        def _getDeps(env):
            return DependencyUtils.install(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                availablePackages,
                {},
                env=env)
        env = Environment()
        deps = _getDeps(env)
        self.assertEqual(['condition-B_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2",
                                   "HELLO": "wOrlD"})
        deps = _getDeps(env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-E_1.0',
                          'condition-G_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        deps = _getDeps(None)
        self.assertEqual(['condition-A_1.0',
                          'condition-B_1.0',
                          'condition-C_1.0',
                          'condition-D_1.0',
                          'condition-E_1.0',
                          'condition-F_1.0',
                          'condition-G_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

    def testPrereq(self):
        availablePackages = TestApiDepends.MANIFEST_MAP

        self.assertEqual(
            availablePackages[PackageIdentifier.fromString(
                "prereq-A_1.0")].getLeafRequires(),
            ["prereq-true_1.0"])
        self.assertEqual(
            availablePackages[PackageIdentifier.fromString(
                "prereq-C_1.0")].getLeafRequires(),
            ["prereq-A_1.0",
             "prereq-B_1.0"])
        self.assertEqual(
            availablePackages[PackageIdentifier.fromString(
                "prereq-D_1.0")].getLeafRequires(),
            ["prereq-true_1.0",
             "prereq-false_1.0"])

    def testPrereqOrder(self):
        availablePackages = TestApiDepends.MANIFEST_MAP
        pi = "prereq-D_1.0"

        prereqs = availablePackages[PackageIdentifier.fromString(
            pi)].getLeafRequires()
        self.assertEqual(["prereq-true_1.0",
                          "prereq-false_1.0"],
                         prereqs)
        prereqs = DependencyUtils.prereq(
            PackageIdentifier.fromStringList([pi]),
            availablePackages,
            {})
        self.assertEqual(["prereq-false_1.0",
                          "prereq-true_1.0"],
                         list(map(str, map(Manifest.getIdentifier, prereqs))))

    def testLatestStrategy(self):
        installedPackages = TestApiDepends.MANIFEST_MAP

        deps = DependencyUtils.installed(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            installedPackages)
        self.assertEqual(['container-E_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

        deps = DependencyUtils.installed(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            installedPackages,
            onlyKeepLatest=True)
        self.assertEqual(['container-C_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

    def testResolveLatest(self):
        pi10 = PackageIdentifier.fromString("version_1.0")
        pi20 = PackageIdentifier.fromString("version_2.0")

        deps = DependencyUtils.install(
            PackageIdentifier.fromStringList(["testlatest_1.0"]),
            TestApiDepends.MANIFEST_MAP,
            {})
        self.assertEqual(['version_2.0',
                          'testlatest_1.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

        deps = DependencyUtils.install(
            PackageIdentifier.fromStringList(["testlatest_1.0"]),
            TestApiDepends.MANIFEST_MAP,
            {pi10: TestApiDepends.MANIFEST_MAP[pi10]})
        self.assertEqual(['version_2.0',
                          'testlatest_1.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

        deps = DependencyUtils.install(
            PackageIdentifier.fromStringList(["testlatest_1.0"]),
            TestApiDepends.MANIFEST_MAP,
            {pi20: TestApiDepends.MANIFEST_MAP[pi20]})
        self.assertEqual(['testlatest_1.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

        deps = DependencyUtils.prereq(
            PackageIdentifier.fromStringList(["testlatest_2.0"]),
            TestApiDepends.MANIFEST_MAP,
            {})
        self.assertEqual(['version_2.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

        deps = DependencyUtils.prereq(
            PackageIdentifier.fromStringList(["testlatest_2.0",
                                              "testlatest_2.1"]),
            TestApiDepends.MANIFEST_MAP,
            {})
        self.assertEqual(['version_2.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

    def testUpgrade(self):
        pi10 = PackageIdentifier.fromString("upgrade_1.0")
        pi11 = PackageIdentifier.fromString("upgrade_1.1")
        pi12 = PackageIdentifier.fromString("upgrade_1.2")

        ideps, udeps = DependencyUtils.upgrade(
            None,
            TestApiDepends.MANIFEST_MAP,
            {
                pi10: TestApiDepends.MANIFEST_MAP[pi10]
            })
        self.assertEqual([],
                         [str(mf.getIdentifier()) for mf in ideps])
        self.assertEqual([],
                         [str(mf.getIdentifier()) for mf in udeps])

        ideps, udeps = DependencyUtils.upgrade(
            None,
            TestApiDepends.MANIFEST_MAP,
            {
                pi10: TestApiDepends.MANIFEST_MAP[pi10],
                pi11: TestApiDepends.MANIFEST_MAP[pi11],
                pi12: TestApiDepends.MANIFEST_MAP[pi12]
            })
        self.assertEqual(["upgrade_2.0"],
                         [str(mf.getIdentifier()) for mf in ideps])
        self.assertEqual(["upgrade_1.1", "upgrade_1.2"],
                         [str(mf.getIdentifier()) for mf in udeps])
