"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import json
import os

from leaf.api import RelengManager
from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.error import LeafException
from leaf.core.jsonutils import jloadfile, jwritefile
from leaf.core.utils import hash_compute, mkdirs
from leaf.model.package import AvailablePackage
from tests.testutils import RESOURCE_FOLDER, LeafTestCaseWithRepo, check_mime


class TestApiRelengManager(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()
        self.rm = RelengManager()

    def test_package_compression(self):
        folder = RESOURCE_FOLDER / "install_1.0"

        def check_all_compressions(extension, mime):
            output_file = self.ws_folder / ("myPackage" + extension)
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
        folder = RESOURCE_FOLDER / "install_1.0"
        artifact = self.ws_folder / "myPackage.leaf"
        info_file = self.ws_folder / "myPackage.leaf.info"

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
        mffile = self.ws_folder / LeafFiles.MANIFEST
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
        with open(str(mffile), "r") as fp:
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
        mffile = self.ws_folder / LeafFiles.MANIFEST

        fragment1 = self.ws_folder / "a.json"
        jwritefile(fragment1, {"a": 1, "info": {"tags": ["tag1"]}})

        fragment2 = self.ws_folder / "b.json"
        jwritefile(fragment2, {"a": 2})

        fragment3 = self.ws_folder / "c.json"
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
        with open(str(mffile), "r") as fp:
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

        mffile = self.ws_folder / LeafFiles.MANIFEST

        try:
            os.environ["LEAF_TEST_VARIABLE"] = "hello"

            fragment1 = self.ws_folder / "a.json"
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
            with open(str(mffile), "r") as fp:
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
        index = self.ws_folder / "index.json"

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
            folder = RESOURCE_FOLDER / pis
            output_file = self.ws_folder / (pis + ".leaf")
            self.rm.create_package(folder, output_file)

        self.rm.generate_index(index, self.ws_folder.glob("condition*.leaf"), prettyprint=True)
        index_content = jloadfile(index)
        self.assertEqual(10, len(index_content[JsonConstants.REMOTE_PACKAGES]))

        self.rm.generate_index(index, self.ws_folder.glob("*.leaf"), prettyprint=False)
        index_content = jloadfile(index)
        self.assertEqual(11, len(index_content[JsonConstants.REMOTE_PACKAGES]))

    def test_index_same_artifact_different_hash(self):
        mkdirs(self.ws_folder / "a")
        mkdirs(self.ws_folder / "b")

        self.rm.generate_manifest(
            self.ws_folder / "a" / LeafFiles.MANIFEST,
            info_map={JsonConstants.INFO_NAME: "foo", JsonConstants.INFO_VERSION: "1", JsonConstants.INFO_DESCRIPTION: "Some description"},
        )

        self.rm.generate_manifest(
            self.ws_folder / "b" / LeafFiles.MANIFEST,
            info_map={JsonConstants.INFO_NAME: "foo", JsonConstants.INFO_VERSION: "1", JsonConstants.INFO_DESCRIPTION: "Different description"},
        )

        self.rm.create_package(self.ws_folder / "a", self.ws_folder / "a.leaf")
        self.rm.create_package(self.ws_folder / "b", self.ws_folder / "b.leaf")

        self.rm.generate_index(self.ws_folder / "indexA.json", [self.ws_folder / "a.leaf", self.ws_folder / "a.leaf"], prettyprint=True)
        self.rm.generate_index(self.ws_folder / "indexB.json", [self.ws_folder / "b.leaf", self.ws_folder / "b.leaf"], prettyprint=True)
        with self.assertRaises(LeafException):
            self.rm.generate_index(self.ws_folder / "indexAB.json", [self.ws_folder / "a.leaf", self.ws_folder / "b.leaf"], prettyprint=True)
