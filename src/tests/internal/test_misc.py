"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from pathlib import Path
from random import shuffle
from tempfile import mktemp

from leaf.core.constants import LeafFiles
from leaf.core.error import LeafException
from leaf.core.jsonutils import JsonObject, jloadfile, jwritefile
from leaf.core.lock import LockFile
from leaf.model.modelutils import keep_latest
from leaf.model.package import AvailablePackage, InstalledPackage, PackageIdentifier
from leaf.model.remote import Remote
from leaf.model.steps import VariableResolver
from tests.testutils import TEST_REMOTE_PACKAGE_SOURCE, LeafTestCase


class TestMisc(LeafTestCase):
    def test_json(self):
        jo = JsonObject({})
        self.assertIsNone(jo.jsonpath(["a"]))
        self.assertIsNotNone(jo.jsonpath(["a"], {}))
        self.assertIsNotNone(jo.jsonpath(["a"]))

        self.assertIsNone(jo.jsonpath(["a", "b"]))
        self.assertIsNotNone(jo.jsonpath(["a", "b"], {}))
        self.assertIsNotNone(jo.jsonpath(["a", "b"]))

        self.assertIsNone(jo.jsonpath(["a", "b", "c"]))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        tmpfile = Path(mktemp(".json", "leaf-ut"))
        jwritefile(tmpfile, jo.json, pp=True)
        jo = JsonObject(jloadfile(tmpfile))

        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        with self.assertRaises(ValueError):
            jo.jsonget("z", mandatory=True)
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "b", "c", "d"])
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "d", "e"])

    def test_sort_pi(self):
        a10 = PackageIdentifier.parse("a_1.0")
        a11 = PackageIdentifier.parse("a_1.1")
        a20 = PackageIdentifier.parse("a_2.0")
        a21 = PackageIdentifier.parse("a_2.1")
        b10 = PackageIdentifier.parse("b_1.0")
        b11 = PackageIdentifier.parse("b_1.1")
        b20 = PackageIdentifier.parse("b_2.0")
        b21 = PackageIdentifier.parse("b_2.1")

        inputlist = [a10, a11, a20, a21, b10, b11, b20, b21]
        for _ in range(100):
            shuffle(inputlist)
            latest_pilist = keep_latest([b10, a20, a10, b11, b21, b20, a21, a11])
            self.assertEqual(latest_pilist, [a21, b21])

    def test_variable_resolver(self):

        ip1 = InstalledPackage(TEST_REMOTE_PACKAGE_SOURCE / "version_1.0" / LeafFiles.MANIFEST)
        ip2 = InstalledPackage(TEST_REMOTE_PACKAGE_SOURCE / "version_1.1" / LeafFiles.MANIFEST)
        ip3 = InstalledPackage(TEST_REMOTE_PACKAGE_SOURCE / "version_2.0" / LeafFiles.MANIFEST)

        vr = VariableResolver(ip1, [ip1, ip2, ip3])

        self.assertEqual("version", vr.resolve("@{NAME}"))
        self.assertEqual("1.0", vr.resolve("@{VERSION}"))
        self.assertEqual(str(TEST_REMOTE_PACKAGE_SOURCE / "version_1.0"), vr.resolve("@{DIR}"))

        self.assertEqual("version", vr.resolve("@{NAME:version_1.0}"))
        self.assertEqual("1.0", vr.resolve("@{VERSION:version_1.0}"))
        self.assertEqual(str(TEST_REMOTE_PACKAGE_SOURCE / "version_1.0"), vr.resolve("@{DIR:version_1.0}"))

        self.assertEqual("version", vr.resolve("@{NAME:version_2.0}"))
        self.assertEqual("2.0", vr.resolve("@{VERSION:version_2.0}"))
        self.assertEqual(str(TEST_REMOTE_PACKAGE_SOURCE / "version_2.0"), vr.resolve("@{DIR:version_2.0}"))

        self.assertEqual("version", vr.resolve("@{NAME:version_latest}"))
        self.assertEqual("2.0", vr.resolve("@{VERSION:version_latest}"))
        self.assertEqual(str(TEST_REMOTE_PACKAGE_SOURCE / "version_2.0"), vr.resolve("@{DIR:version_latest}"))

        self.assertEqual("version 1.1 " + str(TEST_REMOTE_PACKAGE_SOURCE / "version_2.0"), vr.resolve("@{NAME} @{VERSION:version_1.1} @{DIR:version_latest}"))

        with self.assertRaises(LeafException):
            vr.resolve("@{NAME} @{VERSION:version_1.2} @{DIR:version_latest}")

    def test_lock_advisory(self):
        advisory = True
        lf = LockFile("/tmp/advisory.lock")

        @lf.acquire(advisory=advisory)
        def foo():
            pass

        lf.acquire(advisory=advisory)
        with lf.acquire(advisory=advisory):
            with lf.acquire(advisory=advisory):
                with lf.acquire(advisory=advisory):
                    foo()
                foo()
            with lf.acquire(advisory=advisory):
                with lf.acquire(advisory=advisory):
                    foo()
                foo()
            foo()

    def test_lock_mandatory(self):
        advisory = False
        lf = LockFile("/tmp/mandatory.lock")

        @lf.acquire(advisory=advisory)
        def foo():
            pass

        lf.acquire(advisory=advisory)

        with lf.acquire(advisory=advisory):
            with self.assertRaises(LeafException):
                with lf.acquire(advisory=advisory):
                    pass
            try:
                with lf.acquire(advisory=advisory):
                    self.fail()
                self.fail()
            except LeafException:
                pass
            with self.assertRaises(LeafException):
                foo()

        with lf.acquire(advisory=advisory):
            pass

    def test_ap_candidates(self):
        remote_file = Remote("remote_file", {"url": "file:///tmp/file/index.json"})
        remote_fs = Remote("remote_fs", {"url": "/tmp/fs/index.json"})
        remote_custom = Remote("remote_custom", {"url": "https://foo.tld/custom/index.json", "priority": 150})
        remote_https = Remote("remote_https", {"url": "https://foo.tld/https/index.json"})
        remote_http = Remote("remote_http", {"url": "http://foo.tld/http/index.json"})
        remote_other = Remote("remote_other", {"url": "nfs://foo.tld/other/index.json"})

        self.assertEqual(100, remote_file.priority)
        self.assertEqual(100, remote_fs.priority)
        self.assertEqual(150, remote_custom.priority)
        self.assertEqual(200, remote_https.priority)
        self.assertEqual(201, remote_http.priority)
        self.assertEqual(500, remote_other.priority)

        ap_json = {"file": "pack.leaf"}
        ap_json["info"] = jloadfile(TEST_REMOTE_PACKAGE_SOURCE / "version_1.0" / LeafFiles.MANIFEST)["info"]

        ap = AvailablePackage(ap_json, remote=remote_other)
        self.assertEqual("nfs://foo.tld/other/pack.leaf", ap.best_candidate.url)

        ap.add_duplicate(AvailablePackage(ap_json, remote=remote_https))
        self.assertEqual("https://foo.tld/https/pack.leaf", ap.best_candidate.url)

        ap.add_duplicate(AvailablePackage(ap_json, remote=remote_http))
        self.assertEqual("https://foo.tld/https/pack.leaf", ap.best_candidate.url)

        ap.add_duplicate(AvailablePackage(ap_json, remote=remote_custom))
        self.assertEqual("https://foo.tld/custom/pack.leaf", ap.best_candidate.url)

        ap.add_duplicate(AvailablePackage(ap_json, remote=remote_file))
        self.assertEqual("file:///tmp/file/pack.leaf", ap.best_candidate.url)

        ap.add_duplicate(AvailablePackage(ap_json, remote=remote_fs))
        self.assertEqual("file:///tmp/file/pack.leaf", ap.best_candidate.url)

        remote_custom.json["priority"] = 1
        self.assertEqual("https://foo.tld/custom/pack.leaf", ap.best_candidate.url)

        remote_custom.json["priority"] = 999
        self.assertEqual("file:///tmp/file/pack.leaf", ap.best_candidate.url)

        remote_custom.json["priority"] = 100
        self.assertEqual("https://foo.tld/custom/pack.leaf", ap.best_candidate.url)
