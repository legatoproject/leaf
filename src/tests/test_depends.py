'''
@author: seb
'''

from collections import OrderedDict
from leaf.constants import LeafFiles
from leaf.coreutils import DynamicDependencyManager
from leaf.model import Manifest, PackageIdentifier, Environment
from pathlib import Path
import unittest
from unittest.case import TestCase


def mkpi(pis):
    return PackageIdentifier.fromString(pis)


def deps2strlist(deps):
    return list(map(str, map(Manifest.getIdentifier, deps)))


class TestDepends(unittest.TestCase):

    MANIFEST_MAP = {}

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        for f in Path("tests/resources/").iterdir():
            manifestFile = f / LeafFiles.MANIFEST
            if manifestFile.exists():
                try:
                    mf = Manifest.parse(manifestFile)
                    TestDepends.MANIFEST_MAP[mf.getIdentifier()] = mf
                except:
                    pass
        print("Found", len(TestDepends.MANIFEST_MAP), LeafFiles.MANIFEST)

    def testSort(self):
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["container-A_1.0",
                                                                              "container-A_2.0"])),
                                                              TestDepends.MANIFEST_MAP,
                                                              Environment(),
                                                              False)
        self.assertEqual(['container-E_1.0',
                          'container-C_1.0',
                          'container-D_1.0',
                          'container-B_1.0',
                          'container-A_2.0',
                          'container-A_1.0'],
                         deps2strlist(deps))

    def testSortReverse(self):
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["container-A_1.0",
                                                                              "container-A_2.0"])),
                                                              TestDepends.MANIFEST_MAP,
                                                              Environment(),
                                                              True)
        self.assertEqual(['container-A_1.0',
                          'container-A_2.0',
                          'container-B_1.0',
                          'container-D_1.0',
                          'container-C_1.0',
                          'container-E_1.0'],
                         deps2strlist(deps))

    def testForInstall(self):
        availablePackages = TestDepends.MANIFEST_MAP
        installedPackages = {}
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["container-A_1.0",
                                                                           "container-A_2.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           Environment())
        self.assertEqual(['container-E_1.0',
                          'container-C_1.0',
                          'container-D_1.0',
                          'container-B_1.0',
                          'container-A_2.0',
                          'container-A_1.0'],
                         deps2strlist(deps))

        pi = mkpi('container-E_1.0')
        installedPackages[pi] = TestDepends.MANIFEST_MAP.get(pi)

        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["container-A_1.0",
                                                                           "container-A_2.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           Environment())
        self.assertEqual(['container-C_1.0',
                          'container-D_1.0',
                          'container-B_1.0',
                          'container-A_2.0',
                          'container-A_1.0'],
                         deps2strlist(deps))

    def testForUninstall(self):

        availablePackages = TestDepends.MANIFEST_MAP
        installedPackages = OrderedDict()

        for ap in DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["container-A_1.0",
                                                                              "container-A_2.0"])),
                                                              availablePackages,
                                                              installedPackages,
                                                              Environment()):
            installedPackages[ap.getIdentifier()] = ap

        self.assertEqual(['container-E_1.0',
                          'container-C_1.0',
                          'container-D_1.0',
                          'container-B_1.0',
                          'container-A_2.0',
                          'container-A_1.0'],
                         deps2strlist(installedPackages.values()))

        deps = DynamicDependencyManager.computeIpToUninstall(list(map(mkpi, ["container-A_1.0"])),
                                                             installedPackages)

        self.assertEqual(['container-A_1.0',
                          'container-B_1.0',
                          'container-E_1.0'],
                         deps2strlist(deps))

    def testConditionalInstall(self):
        availablePackages = TestDepends.MANIFEST_MAP
        installedPackages = {}
        env = Environment()
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["condition_1.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           env)
        self.assertEqual(['condition-B_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["condition_1.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           env)
        self.assertEqual(['condition-A_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["condition_1.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2"})
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["condition_1.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2",
                                   "HELLO": "wOrlD"})
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["condition_1.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-E_1.0',
                          'condition-G_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        pi = mkpi('condition-C_1.0')
        installedPackages[pi] = TestDepends.MANIFEST_MAP.get(pi)

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2",
                                   "HELLO": "wOrlD"})
        deps = DynamicDependencyManager.computeApToInstall(list(map(mkpi, ["condition_1.0"])),
                                                           availablePackages,
                                                           installedPackages,
                                                           env)
        self.assertEqual(['condition-A_1.0',
                          'condition-E_1.0',
                          'condition-G_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

    def testConditionalTree(self):
        availablePackages = TestDepends.MANIFEST_MAP

        env = Environment()
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["condition_1.0"])),
                                                              availablePackages,
                                                              env)
        self.assertEqual(['condition-B_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["condition_1.0"])),
                                                              availablePackages,
                                                              env)
        self.assertEqual(['condition-A_1.0',
                          'condition-D_1.0',
                          'condition-F_1.0',
                          'condition-H_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["condition_1.0"])),
                                                              availablePackages,
                                                              env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2"})
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["condition_1.0"])),
                                                              availablePackages,
                                                              env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-F_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        env = Environment(content={"FOO": "BAR",
                                   "FOO2": "BAR2",
                                   "HELLO": "wOrlD"})
        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["condition_1.0"])),
                                                              availablePackages,
                                                              env)
        self.assertEqual(['condition-A_1.0',
                          'condition-C_1.0',
                          'condition-E_1.0',
                          'condition-G_1.0',
                          'condition_1.0'],
                         deps2strlist(deps))

        deps = DynamicDependencyManager.computeDependencyTree(list(map(mkpi, ["condition_1.0"])),
                                                              availablePackages)
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

        self.assertEqual(availablePackages[mkpi("prereq-A_1.0")].getLeafRequires(),
                         ["prereq-true_1.0"])
        self.assertEqual(availablePackages[mkpi("prereq-C_1.0")].getLeafRequires(),
                         ["prereq-A_1.0",
                          "prereq-B_1.0"])
        self.assertEqual(availablePackages[mkpi("prereq-D_1.0")].getLeafRequires(),
                         ["prereq-true_1.0",
                          "prereq-false_1.0"])


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'TestDepends.testName']
    unittest.main()
