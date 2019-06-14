"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.api import PackageManager
from leaf.model.filtering import MetaPackageFilter
from tests.testutils import LeafTestCaseWithRepo


class TestApiFiltering(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()
        pm = PackageManager()
        pm.create_remote("default", self.remote_url1, insecure=True)
        pm.create_remote("default2", self.remote_url2, insecure=True)
        pm.fetch_remotes()
        self.content = pm.list_available_packages().values()
        self.assertTrue(len(self.content) > 0)

    def test_master(self):
        f = MetaPackageFilter()
        f.only_master_packages()
        print("Filter:", f)
        self.assertEqual(7, len(list(filter(f.matches, self.content))))

    def test_keywords(self):
        f = MetaPackageFilter()
        f.with_keyword("compress")
        print("Filter:", f)
        self.assertEqual(4, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.with_keyword("container")
        print("Filter:", f)
        self.assertEqual(9, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.with_keyword("container,compress")
        print("Filter:", f)
        self.assertEqual(13, len(list(filter(f.matches, self.content))))
        f.with_keyword("gz")
        print("Filter:", f)
        self.assertEqual(1, len(list(filter(f.matches, self.content))))
        f.only_master_packages()
        print("Filter:", f)
        self.assertEqual(0, len(list(filter(f.matches, self.content))))

    def test_tags(self):
        f = MetaPackageFilter()
        f.with_tag("foo")
        print("Filter:", f)
        self.assertEqual(5, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.with_tag("foo,bar")
        print("Filter:", f)
        self.assertEqual(7, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.with_tag("bar")
        print("Filter:", f)
        self.assertEqual(5, len(list(filter(f.matches, self.content))))
        f.with_tag("foo")
        print("Filter:", f)
        self.assertEqual(3, len(list(filter(f.matches, self.content))))
        f.with_tag("foo2")
        print("Filter:", f)
        self.assertEqual(0, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.with_tag("bar")
        print("Filter:", f)
        self.assertEqual(5, len(list(filter(f.matches, self.content))))
        f.with_tag("foo")
        print("Filter:", f)
        self.assertEqual(3, len(list(filter(f.matches, self.content))))
        f.with_keyword("container-A")
        print("Filter:", f)
        self.assertEqual(2, len(list(filter(f.matches, self.content))))

    def test_pkgnames(self):
        f = MetaPackageFilter()
        f.with_names(["container-A", "version"])
        print("Filter:", f)
        self.assertEqual(7, len(list(filter(f.matches, self.content))))
        f.only_master_packages()
        print("Filter:", f)
        self.assertEqual(2, len(list(filter(f.matches, self.content))))
