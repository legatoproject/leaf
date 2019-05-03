"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.api import GPGManager
from leaf.core.constants import LeafConstants, LeafFiles, LeafSettings
from leaf.core.error import LeafException
from leaf.core.utils import download_data
from tests.testutils import TEST_GPG_FINGERPRINT, LeafTestCaseWithCli, LeafTestCaseWithRepo


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
        self.cacheFile = self.cache_folder / LeafFiles.CACHE_REMOTES_FILENAME

    def tearDown(self):
        LeafSettings.GPG_KEYSERVER.value = None
        LeafTestCaseWithCli.tearDown(self)

    def test_simple(self):
        gpg = GPGManager()
        data = download_data(self.remote_url1)

        with self.assertRaises(LeafException):
            gpg.gpg_verify_content(data, self.remote_url1 + LeafConstants.GPG_SIG_EXTENSION)

        gpg.gpg_import_keys(TEST_GPG_FINGERPRINT)

        gpg.gpg_verify_content(data, self.remote_url1 + LeafConstants.GPG_SIG_EXTENSION, TEST_GPG_FINGERPRINT)

        gpg.gpg_verify_content(data, self.remote_url1 + LeafConstants.GPG_SIG_EXTENSION)

        with self.assertRaises(LeafException):
            gpg.gpg_verify_content(data, self.remote_url1 + LeafConstants.GPG_SIG_EXTENSION, "8C20018BE986D5300A346323FAE026860F1F8AEE")

    def test_remote_without_security(self):
        with self.assertRaises(SystemExit):
            self.leaf_exec(("remote", "add"), "default", self.remote_url1)

    def test_remote_insecure(self):
        self.leaf_exec(("remote", "add"), "--insecure", "default", self.remote_url1)
        self.leaf_exec(("remote", "fetch"))

        self.assertTrue(self.cacheFile.exists())

    def test_remote_bad_key(self):
        self.leaf_exec(("remote", "add"), "--gpg", "8C20018BE986D5300A346323FAE026860F1F8AEE", "default", self.remote_url1)
        self.leaf_exec(("remote", "fetch"))

        self.assertFalse(self.cacheFile.exists())

    def test_remote_valid_key(self):
        self.leaf_exec(("remote", "add"), "--gpg", TEST_GPG_FINGERPRINT, "default", self.remote_url1)
        self.leaf_exec(("remote", "fetch"))

        self.leaf_exec(("search"), "-a")
        self.assertTrue(self.cacheFile.exists())
