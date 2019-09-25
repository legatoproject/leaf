"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import json
import os

from jsonschema.exceptions import ValidationError

from leaf.api import RelengManager
from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.error import LeafException
from leaf.core.jsonutils import jloadfile, jwritefile
from leaf.core.utils import hash_compute, mkdirs
from leaf.model.package import AvailablePackage
from tests.testutils import TEST_REMOTE_PACKAGE_SOURCE, LeafTestCaseWithRepo, check_mime


class TestApiRelengManager(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()
        self.rm = RelengManager()

    def test_package_compression(self):
        folder = TEST_REMOTE_PACKAGE_SOURCE / "install_1.0"

        def check_all_compressions(extension, mime):
            output_file = self.workspace_folder / ("myPackage" + extension)
            for args, mime in ((None, "x-tar"), (("."), "x-tar"), (("-z", "."), "gzip"), (("-j", "."), "x-bzip2"), (("-J", "."), "x-xz"), (("-a", "."), mime)):
                self.rm.create_package(folder, output_file, tar_extra_args=args)
                check_mime(output_file, mime)

        check_all_compressions(".bin", "x-tar")
        check_all_compressions(".tar", "x-tar")
        check_all_compressions(".leaf", "x-tar")
        check_all_compressions(".tar.gz", "gzip")
        check_all_compressions(".tar.bz2", "x-bzip2")
        check_all_compressions(".tar.xz", "x-xz")

    def test_external_info_file(self):
        folder = TEST_REMOTE_PACKAGE_SOURCE / "install_1.0"
        artifact = self.workspace_folder / "myPackage.leaf"
        info_file = self.workspace_folder / "myPackage.leaf.info"

        self.rm.create_package(folder, artifact, store_extenal_info=False)
        self.assertTrue(artifact.exists())
        self.assertFalse(info_file.exists())

        self.rm.create_package(folder, artifact, store_extenal_info=True)
        self.assertTrue(artifact.exists())
        self.assertTrue(info_file.exists())
        self.assertEqual(info_file, self.rm.find_external_info_file(artifact))
        self.assertEqual(hash_compute(artifact), AvailablePackage(jloadfile(info_file), None).hashsum)

        with self.assertRaises(LeafException):
            self.rm.create_package(folder, artifact, store_extenal_info=False)

    def test_manifest_info_map(self):
        mffile = self.workspace_folder / LeafFiles.MANIFEST
        self.rm.generate_manifest(
            mffile,
            info_map={
                JsonConstants.INFO_NAME: "foo",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "lorem ipsum",
                JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                JsonConstants.INFO_MASTER: True,
                JsonConstants.INFO_LEAF_MINVER: "0.42",
                JsonConstants.INFO_REQUIRES: ["a_1", "b_1", "a_1"],
                JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)", "a_1"],
                JsonConstants.INFO_TAGS: ["foo", "bar", "foo"],
                "ignored_extra_key": "hello",
            },
        )
        self.assertTrue(mffile.exists())
        with mffile.open() as fp:
            self.assertEqual(
                {
                    JsonConstants.INFO: {
                        JsonConstants.INFO_NAME: "foo",
                        JsonConstants.INFO_VERSION: "1.0",
                        JsonConstants.INFO_DESCRIPTION: "lorem ipsum",
                        JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                        JsonConstants.INFO_MASTER: True,
                        JsonConstants.INFO_LEAF_MINVER: "0.42",
                        JsonConstants.INFO_REQUIRES: ["a_1", "b_1"],
                        JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)"],
                        JsonConstants.INFO_TAGS: ["foo", "bar"],
                    }
                },
                json.load(fp),
            )

    def test_manifest_fragments(self):
        mffile = self.workspace_folder / LeafFiles.MANIFEST

        fragment1 = self.workspace_folder / "a.json"
        jwritefile(fragment1, {"a": 1, "info": {"tags": ["tag1"]}})

        fragment2 = self.workspace_folder / "b.json"
        jwritefile(fragment2, {"a": 2})

        fragment3 = self.workspace_folder / "c.json"
        jwritefile(fragment3, {"b": True, "info": {"tags": ["tag2"]}})

        self.rm.generate_manifest(
            mffile,
            fragment_files=[fragment1, fragment2, fragment3],
            info_map={
                JsonConstants.INFO_NAME: "foo",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_TAGS: ["foo", "bar", "foo"],
                "ignored_extra_key": "hello",
            },
        )
        self.assertTrue(mffile.exists())
        with mffile.open() as fp:
            self.assertEqual(
                {
                    JsonConstants.INFO: {
                        JsonConstants.INFO_NAME: "foo",
                        JsonConstants.INFO_VERSION: "1.0",
                        JsonConstants.INFO_TAGS: ["tag1", "tag2", "foo", "bar"],
                    },
                    "a": 2,
                    "b": True,
                },
                json.load(fp),
            )

    def test_manifest_with_env(self, resolve_env=True):

        mffile = self.workspace_folder / LeafFiles.MANIFEST

        try:
            os.environ["LEAF_TEST_VARIABLE"] = "hello"

            fragment1 = self.workspace_folder / "a.json"
            jwritefile(fragment1, {"a": "#{LEAF_TEST_VARIABLE} #{LEAF_TEST_VARIABLE}"})

            self.rm.generate_manifest(
                mffile,
                fragment_files=[fragment1],
                info_map={
                    JsonConstants.INFO_NAME: "foo",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "#{LEAF_TEST_VARIABLE} #{LEAF_TEST_VARIABLE}",
                },
                resolve_envvars=resolve_env,
            )
            self.assertTrue(mffile.exists())
            with mffile.open() as fp:
                motif = "hello hello" if resolve_env else "#{LEAF_TEST_VARIABLE} #{LEAF_TEST_VARIABLE}"
                self.assertEqual(
                    {
                        JsonConstants.INFO: {JsonConstants.INFO_NAME: "foo", JsonConstants.INFO_VERSION: "1.0", JsonConstants.INFO_DESCRIPTION: motif},
                        "a": motif,
                    },
                    json.load(fp),
                )

        finally:
            del os.environ["LEAF_TEST_VARIABLE"]

    def test_manifest_without_env(self):
        self.test_manifest_with_env(resolve_env=False)

    def test_index(self):
        index = self.workspace_folder / "index.json"

        # Build some packages
        for pis in (
            "install_1.0",
            "condition_1.0",
            "condition-A_1.0",
            "condition-A_2.0",
            "condition-B_1.0",
            "condition-C_1.0",
            "condition-D_1.0",
            "condition-E_1.0",
            "condition-F_1.0",
            "condition-G_1.0",
            "condition-H_1.0",
        ):
            folder = TEST_REMOTE_PACKAGE_SOURCE / pis
            output_file = self.workspace_folder / (pis + ".leaf")
            self.rm.create_package(folder, output_file)

        self.rm.generate_index(index, self.workspace_folder.glob("condition*.leaf"), prettyprint=True)
        index_content = jloadfile(index)
        self.assertEqual(10, len(index_content[JsonConstants.REMOTE_PACKAGES]))

        self.rm.generate_index(index, self.workspace_folder.glob("*.leaf"), prettyprint=False)
        index_content = jloadfile(index)
        self.assertEqual(11, len(index_content[JsonConstants.REMOTE_PACKAGES]))

    def test_index_same_artifact_different_hash(self):
        mkdirs(self.workspace_folder / "a")
        mkdirs(self.workspace_folder / "b")

        self.rm.generate_manifest(
            self.workspace_folder / "a" / LeafFiles.MANIFEST,
            info_map={JsonConstants.INFO_NAME: "foo", JsonConstants.INFO_VERSION: "1", JsonConstants.INFO_DESCRIPTION: "Some description"},
        )

        self.rm.generate_manifest(
            self.workspace_folder / "b" / LeafFiles.MANIFEST,
            info_map={JsonConstants.INFO_NAME: "foo", JsonConstants.INFO_VERSION: "1", JsonConstants.INFO_DESCRIPTION: "Different description"},
        )

        self.rm.create_package(self.workspace_folder / "a", self.workspace_folder / "a.leaf")
        self.rm.create_package(self.workspace_folder / "b", self.workspace_folder / "b.leaf")

        self.rm.generate_index(self.workspace_folder / "indexA.json", [self.workspace_folder / "a.leaf", self.workspace_folder / "a.leaf"], prettyprint=True)
        self.rm.generate_index(self.workspace_folder / "indexB.json", [self.workspace_folder / "b.leaf", self.workspace_folder / "b.leaf"], prettyprint=True)
        with self.assertRaises(LeafException):
            self.rm.generate_index(
                self.workspace_folder / "indexAB.json", [self.workspace_folder / "a.leaf", self.workspace_folder / "b.leaf"], prettyprint=True
            )

    def test_invalid_manifest(self):
        pkg_folder = self.workspace_folder / "mypackage_1.0"
        mffile = pkg_folder / "manifest.json"
        artifact = self.workspace_folder / "foo.leaf"
        mkdirs(pkg_folder)

        # No name/version
        jwritefile(mffile, {})
        with self.assertRaises(ValidationError):
            self.rm.create_package(pkg_folder, artifact)

        # Invalid name
        jwritefile(mffile, {"info": {"name": "my_package", "version": "1.0"}})
        with self.assertRaises(ValidationError):
            self.rm.create_package(pkg_folder, artifact)

        # Invalid version
        jwritefile(mffile, {"info": {"name": "mypackage", "version": "_1.0"}})
        with self.assertRaises(ValidationError):
            self.rm.create_package(pkg_folder, artifact)

        # Invalid dependency
        jwritefile(mffile, {"info": {"name": "mypackage", "version": "1.0", "depends": ["foo-bar"]}})
        with self.assertRaises(ValidationError):
            self.rm.create_package(pkg_folder, artifact)
        jwritefile(mffile, {"info": {"name": "mypackage", "version": "1.0", "requires": ["foo_bar(FOO=BAR)(TEDDY!=BEAR)"]}})
        with self.assertRaises(ValidationError):
            self.rm.create_package(pkg_folder, artifact)
        jwritefile(mffile, {"info": {"name": "mypackage", "version": "1.0", "depends": ["foo_bar(FOO=BAR)(TEDDY!=BEAR)"], "requires": ["teddy_bear"]}})
        self.rm.create_package(pkg_folder, artifact)

        # Valid model
        jwritefile(mffile, {"info": {"name": "mypackage", "version": "1.0"}})
        self.rm.create_package(pkg_folder, artifact)

        # Empty step
        jwritefile(mffile, {"info": {"name": "mypackage", "version": "1.0"}, "install": [{}]})
        with self.assertRaises(ValidationError):
            self.rm.create_package(pkg_folder, artifact)
