'''
Created on 26 févr. 2018

@author: seb
'''

from leaf.constants import LeafConstants
from pathlib import Path
import unittest
from unittest.case import TestCase

from leaf.core import DependencyManager
from leaf.model import Manifest, PackageIdentifier


class DependencyTest(unittest.TestCase):

    MANIFEST_MAP = {}

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        for f in Path("tests/resources/").iterdir():
            manifestFile = f / LeafConstants.MANIFEST
            if manifestFile.exists():
                try:
                    mf = Manifest.parse(manifestFile)
                    mf.getLeafDepends()
                    DependencyTest.MANIFEST_MAP[mf.getIdentifier()] = mf
                except:
                    pass
        print("Found", len(DependencyTest.MANIFEST_MAP), LeafConstants.MANIFEST)

    def checkContains(self, piList, pisList, order=False):
        for pis in pisList:
            self.assertTrue(PackageIdentifier.fromString(pis)
                            in piList, msg="Missing " + pis)
        self.assertEqual(len(piList), len(pisList))
        if order:
            for i in range(len(piList)):
                self.assertEqual(piList[i],
                                 PackageIdentifier.fromString(pisList[i]))

    def dump(self, message, items):
        print(message)
        for i in items:
            print("  ", str(i))

    def testAdditivity(self):
        dm = DependencyManager()
        dm.addContent(DependencyTest.MANIFEST_MAP)

        deps = dm.getDependencyTree([PackageIdentifier.fromString("container-A_1.0"),
                                     PackageIdentifier.fromString("container-A_2.0")])
        self.checkContains(deps,
                           ["container-A_1.0",
                            "container-A_2.0",
                            "container-B_1.0",
                            "container-C_1.0",
                            "container-D_1.0",
                            "container-E_1.0"])

    def testSort(self):
        dm = DependencyManager()
        dm.addContent(DependencyTest.MANIFEST_MAP)

        deps = dm.getDependencyTree(
            [PackageIdentifier.fromString("container-A_1.0")])
        deps = dm.filterAndSort(deps)
        self.checkContains(deps,
                           ["container-E_1.0",
                            "container-C_1.0",
                            "container-B_1.0",
                            "container-A_1.0"],
                           order=True)

    def testSortReverse(self):
        dm = DependencyManager()
        dm.addContent(DependencyTest.MANIFEST_MAP)

        deps = dm.getDependencyTree(
            [PackageIdentifier.fromString("container-A_1.0")])
        deps = dm.filterAndSort(deps,
                                reverse=True)
        self.checkContains(deps,
                           ["container-A_1.0",
                            "container-B_1.0",
                            "container-C_1.0",
                            "container-E_1.0"],
                           order=True)

    def testSortFiltered(self):
        dm = DependencyManager()
        dm.addContent(DependencyTest.MANIFEST_MAP)

        deps = dm.getDependencyTree(
            [PackageIdentifier.fromString("container-A_1.0")])
        deps = dm.filterAndSort(deps,
                                ignoredPiList=[PackageIdentifier.fromString("container-B_1.0")])
        self.checkContains(deps,
                           ["container-E_1.0",
                            "container-C_1.0",
                            "container-A_1.0"],
                           order=True)

    def testMaintainDependencies(self):
        dm = DependencyManager()
        dm.addContent(DependencyTest.MANIFEST_MAP)

        deps = dm.getDependencyTree(
            [PackageIdentifier.fromString("container-A_1.0")])
        deps = dm.filterAndSort(deps,
                                ignoredPiList=[PackageIdentifier.fromString("container-B_1.0")])
        dm = DependencyManager()
        for pis in ["container-A_1.0",
                    "container-A_2.0",
                    "container-B_1.0",
                    "container-C_1.0",
                    "container-D_1.0",
                    "container-E_1.0"]:
            pi = PackageIdentifier.fromString(pis)
            dm.addContent({pi: DependencyTest.MANIFEST_MAP.get(pi)})
        deps = dm.maintainDependencies(deps)
        self.checkContains(deps,
                           ["container-A_1.0"],
                           order=True)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'DependencyTest.testName']
    unittest.main()
