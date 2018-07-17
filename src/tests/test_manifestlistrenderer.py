'''
@author: nico
'''

from tests.testutils import LeafCliWrapper, LEAF_UT_SKIP, AbstractTestWithRepo
import unittest

PRINT_PREFIX = "[CLI INPUT]"


class TestManifestListRenderer_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.leafExec("config", "--root", self.getInstallFolder())

    def addDefaultRemote(self):
        self.print("Add default remote")
        self.leafExec(("remote", "add"), "default", self.getRemoteUrl())
        self.print("Fetch it")
        self.leafExec(("remote", "fetch"))

    def testSearch(self):
        self.print("Search packages when no remote is set")
        with self.assertStdout(
                stdout="search0.out"):
            self.leafExec(("search"))
        self.addDefaultRemote()
        self.print("Search packages when 1 remote is set")
        with self.assertStdout(
                stdout="search1.out"):
            self.leafExec(("search"))

    def testPackageList(self):
        self.addDefaultRemote()
        self.print("List packages when nothing is installed")
        with self.assertStdout(
                stdout="pkglist0.out"):
            self.leafExec(("package", "list"))
        self.print("Install package")
        self.leafExec(["package", "install"], "container-A_1.0")
        self.print("List packages when 1 package is installed")
        with self.assertStdout(
                stdout="pkglist1.out",
                variables={
                    "{INSTALL_FOLDER}": str(self.getInstallFolder())}):
            self.leafExec(("package", "list"))

    def print(self, msg):
        print(PRINT_PREFIX, " ".join(self.postVerbArgs), msg)


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestManifestListRenderer_Verbose(TestManifestListRenderer_Default):
    def __init__(self, methodName):
        TestManifestListRenderer_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestManifestListRenderer_Quiet(TestManifestListRenderer_Default):
    def __init__(self, methodName):
        TestManifestListRenderer_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


if __name__ == "__main__":
    unittest.main()
