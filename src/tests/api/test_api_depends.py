'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import unittest
from collections import OrderedDict
from unittest.case import TestCase

from leaf.constants import LeafFiles
from leaf.core.dependencies import DependencyManager, DependencyStrategy, \
    DependencyType
from leaf.model.environment import Environment
from leaf.model.package import Manifest, PackageIdentifier
from tests.testutils import RESOURCE_FOLDER


def deps2strlist(deps):
    return list(map(str, map(Manifest.getIdentifier, deps)))


class TestDepends(unittest.TestCase):

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
                    TestDepends.MANIFEST_MAP[mf.getIdentifier()] = mf
                except Exception:
                    pass
        print("Found", len(TestDepends.MANIFEST_MAP), LeafFiles.MANIFEST)

    def testForInstall(self):
        availablePackages = TestDepends.MANIFEST_MAP
        installedPackages = {}
        deps = DependencyManager.compute(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            DependencyType.INSTALL,
            apMap=availablePackages,
            ipMap=installedPackages,
            env=Environment())
        self.assertEqual(['container-E_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         deps2strlist(deps))

        pi = PackageIdentifier.fromString('container-E_1.0')
        installedPackages[pi] = TestDepends.MANIFEST_MAP.get(pi)

        deps = DependencyManager.compute(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            DependencyType.INSTALL,
            apMap=availablePackages,
            ipMap=installedPackages,
            env=Environment())
        self.assertEqual(['container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         deps2strlist(deps))

    def testForUninstall(self):

        availablePackages = TestDepends.MANIFEST_MAP
        installedPackages = OrderedDict()

        for ap in DependencyManager.compute(
                PackageIdentifier.fromStringList(["container-A_1.0",
                                                  "container-A_2.0"]),
                DependencyType.INSTALL,
                ipMap=installedPackages,
                apMap=availablePackages):
            installedPackages[ap.getIdentifier()] = ap

        self.assertEqual(['container-E_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         deps2strlist(installedPackages.values()))

        deps = DependencyManager.compute(
            PackageIdentifier.fromStringList(["container-A_1.0"]),
            DependencyType.UNINSTALL,
            ipMap=installedPackages)

        self.assertEqual(['container-A_1.0',
                          'container-B_1.0',
                          'container-E_1.0'],
                         deps2strlist(deps))

    def testConditionalInstall(self):
        availablePackages = TestDepends.MANIFEST_MAP
        installedPackages = {}

        def _getDeps(env):
            return DependencyManager.compute(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                DependencyType.INSTALL,
                apMap=availablePackages,
                ipMap=installedPackages,
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
        installedPackages[pi] = TestDepends.MANIFEST_MAP.get(pi)

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
        availablePackages = TestDepends.MANIFEST_MAP

        def _getDeps(env):
            return DependencyManager.compute(
                PackageIdentifier.fromStringList(["condition_1.0"]),
                DependencyType.AVAILABLE,
                apMap=availablePackages,
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
        availablePackages = TestDepends.MANIFEST_MAP

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
        availablePackages = TestDepends.MANIFEST_MAP
        pi = "prereq-D_1.0"

        prereqs = availablePackages[PackageIdentifier.fromString(
            pi)].getLeafRequires()
        self.assertEqual(["prereq-true_1.0",
                          "prereq-false_1.0"],
                         prereqs)
        prereqs = DependencyManager.compute(
            PackageIdentifier.fromStringList([pi]),
            DependencyType.PREREQ,
            apMap=availablePackages,
            ipMap={})
        self.assertEqual(["prereq-false_1.0",
                          "prereq-true_1.0"],
                         list(map(str, map(Manifest.getIdentifier, prereqs))))

    def testLatest(self):
        availablePackages = TestDepends.MANIFEST_MAP

        deps = DependencyManager.compute(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            depType=DependencyType.INSTALL,
            strategy=DependencyStrategy.ALL_VERSIONS,
            apMap=availablePackages,
            ipMap={})
        self.assertEqual(['container-E_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-A_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))

        deps = DependencyManager.compute(
            PackageIdentifier.fromStringList(["container-A_1.0",
                                              "container-A_2.0"]),
            depType=DependencyType.INSTALL,
            strategy=DependencyStrategy.LATEST_VERSION,
            apMap=availablePackages,
            ipMap={})
        self.assertEqual(['container-C_1.0',
                          'container-D_1.0',
                          'container-A_2.0'],
                         list(map(str, map(Manifest.getIdentifier, deps))))