'''
Created on 9 août 2018

@author: seb
'''
import os
import unittest

from leaf.constants import LeafConstants, LeafFiles, EnvConstants
from leaf.core.packagemanager import GPGManager
from leaf.format.logger import Verbosity
from leaf.utils import downloadData
from tests.testutils import LeafCliWrapper, TEST_GPG_FINGERPRINT,\
    AbstractTestWithRepo


class TestGPG(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)
        self.postVerbArgs += ["--verbose"]

    def setUp(self):
        # bypass LeafCliWrapper.setup
        # because we don't want default remote configured here
        AbstractTestWithRepo.setUp(self)
        os.environ[EnvConstants.GPG_KEYSERVER] = "keyserver.ubuntu.com"
        self.cacheFile = self.getCacheFolder() / LeafFiles.CACHE_REMOTES_FILENAME

    def tearDown(self):
        LeafCliWrapper.tearDown(self)
        del os.environ[EnvConstants.GPG_KEYSERVER]

    def testSimple(self):
        gpg = GPGManager(Verbosity.VERBOSE, True)
        print("GPG Home:", gpg.gpgHome)
        data = downloadData(self.getRemoteUrl())

        with self.assertRaises(ValueError):
            gpg.gpgVerifyContent(
                data,
                self.getRemoteUrl() + LeafConstants.GPG_SIG_EXTENSION)

        gpg.gpgImportKeys(TEST_GPG_FINGERPRINT)

        gpg.gpgVerifyContent(
            data,
            self.getRemoteUrl() + LeafConstants.GPG_SIG_EXTENSION,
            TEST_GPG_FINGERPRINT)

        gpg.gpgVerifyContent(
            data,
            self.getRemoteUrl() + LeafConstants.GPG_SIG_EXTENSION)

        with self.assertRaises(ValueError):
            gpg.gpgVerifyContent(
                data,
                self.getRemoteUrl() + LeafConstants.GPG_SIG_EXTENSION,
                "8C20018BE986D5300A346323FAE026860F1F8AEE")

    def testRemoteWithoutSecurity(self):
        with self.assertRaises(SystemExit):
            self.leafExec(("remote", "add"),
                          "default", self.getRemoteUrl())

    def testRemoteInsecure(self):
        self.leafExec(("remote", "add"),
                      "--insecure",
                      "default", self.getRemoteUrl())
        self.leafExec(("remote", "fetch"))

        self.assertTrue(self.cacheFile.exists())

    def testRemoteBadKey(self):
        self.leafExec(("remote", "add"),
                      "--gpg", "8C20018BE986D5300A346323FAE026860F1F8AEE",
                      "default", self.getRemoteUrl())
        self.leafExec(("remote", "fetch"))

        self.assertFalse(self.cacheFile.exists())

    def testRemoteValidKey(self):
        self.leafExec(("remote", "add"),
                      "--gpg", TEST_GPG_FINGERPRINT,
                      "default", self.getRemoteUrl())
        self.leafExec(("remote", "fetch"))

        self.leafExec(("search"), "-a")
        self.assertTrue(self.cacheFile.exists())


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
