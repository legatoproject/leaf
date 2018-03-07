'''
Created on 23 nov. 2017

@author: seb
'''

from leaf.cli_packagemanager import PackageManagerCli
import os
import unittest

from tests.utils import TestWithRepository


SEPARATOR = "--------------------"


class CliTestDefault(TestWithRepository):

    def __init__(self, methodName):
        TestWithRepository.__init__(self, methodName)
        self.preCommandArg = None
        self.postCommandArg = None

    def setUp(self):
        TestWithRepository.setUp(self)
        self.configFile = TestWithRepository.ROOT_FOLDER / "cli-config.json"

    def initLeafConfig(self, setRoot=True, addRemote=True, refresh=True):
        self.configFile = TestWithRepository.ROOT_FOLDER / "cli-config.json"
        if self.configFile.exists():
            os.remove(str(self.configFile))
        if setRoot:
            self.leafExec("config", "--root", self.getInstallFolder())
            if addRemote:
                self.leafExec("remote", "--add", self.getRemoteUrl())
                if refresh:
                    self.leafExec("refresh")

    def leafExec(self, verb, *args, checkRc=True):
        command = ["--config", str(self.configFile)]
        if self.preCommandArg is not None:
            command.append(self.preCommandArg)
        command.append(verb)
        if self.postCommandArg is not None:
            command.append(self.postCommandArg)
        for a in args:
            command.append(str(a))
        print(SEPARATOR,
              "[" + type(self).__name__ + "]",
              "Execute:",
              " ".join(command))
        out = PackageManagerCli().execute(command)
        print(SEPARATOR + SEPARATOR + SEPARATOR)
        if checkRc:
            self.assertEqual(0, out, " ".join(command))
        return out

    def checkContent(self, *pisList):
        for pis in pisList:
            folder = self.getInstallFolder() / str(pis)
            self.assertTrue(folder.is_dir(), msg=str(folder))
        folderItemCount = 0
        for i in self.getInstallFolder().iterdir():
            if i.is_dir():
                folderItemCount += 1
        self.assertEqual(len(pisList),
                         folderItemCount)

    def testConfig(self):
        self.initLeafConfig(False)
        self.leafExec("config")
        self.initLeafConfig()
        self.leafExec("config")

    def testRemote(self):
        self.initLeafConfig(False)
        self.leafExec("remote", "--add", self.getRemoteUrl())
        self.leafExec("remote")
        self.leafExec("remote", "--rm", self.getRemoteUrl())
        self.leafExec("remote")

    def testSearch(self):
        self.initLeafConfig()
        self.leafExec("search")
        self.leafExec("search", "--all")

    def testDepends(self):
        self.initLeafConfig()
        self.leafExec("install", "container-A_1.0")
        self.leafExec("dependencies", "container-A_2.0")
        self.leafExec("dependencies", "-i", "container-A_2.0")

    def testDownload(self):
        self.initLeafConfig()
        self.leafExec("download", "container-A_2.1")

    def testInstall(self):
        self.initLeafConfig()
        self.leafExec("install", "container-A")
        self.leafExec("list")
        self.leafExec("list", "--all")
        self.checkContent('container-A_2.1',
                          'container-C_1.0',
                          'container-D_1.0')

    def testEnv(self):
        self.initLeafConfig()
        self.leafExec("install", "env-A_1.0")
        self.leafExec("env", "env-A_1.0")

    def testInstallWithSteps(self):
        self.initLeafConfig()
        self.leafExec("install", "install_1.0")
        self.checkContent('install_1.0')

    def testInstallUninstallKeep(self):
        self.initLeafConfig()
        self.leafExec("install", "container-A_1.0")
        self.checkContent('container-A_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-E_1.0')
        self.leafExec("install", "container-A_2.0")
        self.checkContent('container-A_1.0',
                          'container-A_2.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-D_1.0',
                          'container-C_1.0')
        self.leafExec("remove", "container-A_1.0")
        self.checkContent('container-A_2.0',
                          'container-C_1.0',
                          'container-D_1.0')

    def testClean(self):
        self.initLeafConfig()
        self.leafExec("clean")

    def testMissingApt(self):
        self.initLeafConfig()
        self.leafExec("dependencies", "--apt",
                      "deb_1.0", "failure-depends-deb_1.0")
        with self.assertRaises(ValueError):
            self.leafExec("install", "failure-depends-deb_1.0")
        self.leafExec("install", "--skip-apt", "failure-depends-deb_1.0")
        self.checkContent('failure-depends-deb_1.0')


class CliTestVerbose(CliTestDefault):
    def __init__(self, methodName):
        CliTestDefault.__init__(self, methodName)
        self.preCommandArg = None
        self.postCommandArg = "--verbose"


class CliTestQuiet(CliTestDefault):
    def __init__(self, methodName):
        CliTestDefault.__init__(self, methodName)
        self.preCommandArg = None
        self.postCommandArg = "--quiet"


class CliTestJson(CliTestDefault):
    def __init__(self, methodName):
        CliTestDefault.__init__(self, methodName)
        self.preCommandArg = "--json"
        self.postCommandArg = None


if __name__ == "__main__":
    unittest.main()
