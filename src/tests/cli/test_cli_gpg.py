'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from leaf.api import GPGManager
from leaf.core.constants import LeafConstants, LeafFiles, LeafSettings
from leaf.core.error import LeafException
from leaf.core.utils import downloadData
from tests.testutils import (TEST_GPG_FINGERPRINT, LeafTestCaseWithRepo,
                             LeafTestCaseWithCli)


class TestGPG(LeafTestCaseWithCli):

    def __init__(self, *args, **kwargs):
        LeafTestCaseWithCli.__init__(self, *args, **kwargs)

    @classmethod
    def setUpClass(cls):
        LeafTestCaseWithCli.setUpClass()
        LeafSettings.VERBOSITY.value = "verbose"

    def setUp(self):
        # bypass LeafTestCaseWithCli.setup
        # because we don't want default remote configured here
        LeafTestCaseWithRepo.setUp(self)
        LeafSettings.GPG_KEYSERVER.value = "keyserver.ubuntu.com"
        self.cacheFile = self.getCacheFolder() / LeafFiles.CACHE_REMOTES_FILENAME

    def tearDown(self):
        LeafTestCaseWithCli.tearDown(self)

    def testSimple(self):
        gpg = GPGManager()
        print("GPG Home:", gpg.gpgHome)
        data = downloadData(self.getRemoteUrl())

        with self.assertRaises(LeafException):
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

        with self.assertRaises(LeafException):
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
