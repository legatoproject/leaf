"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import json
import os
import time

from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.jsonutils import jloadfile, jwritefile
from leaf.core.utils import hash_compute
from tests.testutils import TEST_REMOTE_PACKAGE_SOURCE, LeafTestCaseWithCli, check_mime


class TestCliRelengManager(LeafTestCaseWithCli):
    def test_package_compression(self):
        folder = TEST_REMOTE_PACKAGE_SOURCE / "install_1.0"

        def check_all_compressions(extension, default_mime):
            output_file = self.workspace_folder / ("myPackage" + extension)
            for compression, mime in (("-z", "gzip"), ("-j", "x-bzip2"), ("-J", "x-xz"), ("-a", default_mime)):
                self.leaf_exec(("build", "pack"), "--output", output_file, "--input", folder, "--", compression, ".")
                check_mime(output_file, mime)

        check_all_compressions(".bin", "x-tar")
        check_all_compressions(".tar", "x-tar")
        check_all_compressions(".tar.gz", "gzip")
        check_all_compressions(".tar.bz2", "x-bzip2")
        check_all_compressions(".tar.xz", "x-xz")
        check_all_compressions(".leaf", "x-tar")

    def test_external_hash_file(self):
        folder = TEST_REMOTE_PACKAGE_SOURCE / "install_1.0"
        output_file = self.workspace_folder / "myPackage.leaf"
        info_file = self.workspace_folder / "myPackage.leaf.info"

        self.leaf_exec(("build", "pack"), "--no-info", "--output", output_file, "--input", folder)
        self.assertTrue(output_file.exists())
        self.assertFalse(info_file.exists())

        self.leaf_exec(("build", "pack"), "--output", output_file, "--input", folder)
        self.assertTrue(output_file.exists())
        self.assertTrue(info_file.exists())

        self.leaf_exec(("build", "pack"), "--no-info", "--output", output_file, "--input", folder, expected_rc=2)

    def test_manifest_generation(self):
        mffile = self.workspace_folder / LeafFiles.MANIFEST

        fragment1 = self.workspace_folder / "a.json"
        jwritefile(fragment1, {"#{LEAF_TEST_VARIABLE}": "#{LEAF_TEST_VARIABLE}", "a": 1, "info": {"tags": ["tag1"]}})

        fragment2 = self.workspace_folder / "b.json"
        jwritefile(fragment2, {"a": 2})

        fragment3 = self.workspace_folder / "c.json"
        jwritefile(fragment3, {"b": True, "info": {"tags": ["tag2"]}})

        try:
            os.environ["LEAF_TEST_VARIABLE"] = "hello"
            self.leaf_exec(
                ("build", "manifest"),
                "--output",
                self.workspace_folder,
                "--append",
                fragment1,
                "--append",
                fragment2,
                "--append",
                fragment3,
                "--env",
                "--name",
                "foo",
                "--version",
                "1.0",
                "--description",
                "lorem ipsum #{LEAF_TEST_VARIABLE}",
                "--date",
                "2012-12-12 12:12:12",
                "--master",
                "true",
                "--minver",
                "0.42",
                "--requires",
                "a_1",
                "--requires",
                "b_1",
                "--requires",
                "a_1",
                "--depends",
                "a_1",
                "--depends",
                "b_1(FOO=BAR)",
                "--depends",
                "a_1",
                "--tag",
                "foo",
                "--tag",
                "bar",
                "--tag",
                "foo",
                "--upgradable",
                "true",
            )
        finally:
            del os.environ["LEAF_TEST_VARIABLE"]

        self.assertTrue(mffile.exists())
        with mffile.open() as fp:
            self.assertEqual(
                {
                    "hello": "hello",
                    "a": 2,
                    "b": True,
                    JsonConstants.INFO: {
                        JsonConstants.INFO_NAME: "foo",
                        JsonConstants.INFO_VERSION: "1.0",
                        JsonConstants.INFO_DESCRIPTION: "lorem ipsum hello",
                        JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                        JsonConstants.INFO_MASTER: True,
                        JsonConstants.INFO_LEAF_MINVER: "0.42",
                        JsonConstants.INFO_REQUIRES: ["a_1", "b_1"],
                        JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)"],
                        JsonConstants.INFO_TAGS: ["tag1", "tag2", "foo", "bar"],
                        JsonConstants.INFO_AUTOUPGRADE: True,
                    },
                },
                json.load(fp),
            )

    def test_index_generation(self):
        index = self.workspace_folder / "index.json"

        # Build some packages
        self.leaf_exec(("build", "pack"), "--output", self.workspace_folder / "a.leaf", "--input", TEST_REMOTE_PACKAGE_SOURCE / "install_1.0")
        self.leaf_exec(("build", "pack"), "--output", self.workspace_folder / "b.leaf", "--input", TEST_REMOTE_PACKAGE_SOURCE / "condition_1.0")

        self.leaf_exec(
            ("build", "index"),
            "--resolve",
            "--output",
            index,
            "--name",
            "Name",
            "--description",
            "Description here",
            "--prettyprint",
            self.workspace_folder / "a.leaf",
        )
        self.assertTrue(index.exists())
        self.assertEqual(1, len(jloadfile(index)[JsonConstants.REMOTE_PACKAGES]))

        self.leaf_exec(
            ("build", "index"),
            "--resolve",
            "--output",
            index,
            "--name",
            "Name",
            "--description",
            "Description here",
            "--no-info",
            self.workspace_folder / "a.leaf",
            self.workspace_folder / "b.leaf",
        )
        self.assertTrue(index.exists())
        self.assertEqual(2, len(jloadfile(index)[JsonConstants.REMOTE_PACKAGES]))

    def test_index_generation_with_input_file(self):
        index = self.workspace_folder / "index.json"
        input_file = self.workspace_folder / "input.list"

        # Build some packages
        self.leaf_exec(("build", "pack"), "--output", self.workspace_folder / "a.leaf", "--input", TEST_REMOTE_PACKAGE_SOURCE / "install_1.0")
        self.leaf_exec(("build", "pack"), "--output", self.workspace_folder / "b.leaf", "--input", TEST_REMOTE_PACKAGE_SOURCE / "condition_1.0")

        with input_file.open("w") as fp:
            fp.write("# This is a comment \n")
        self.leaf_exec(
            ("build", "index"), "--resolve", "--output", index, "--name", "Name", "--description", "Description here", "--prettyprint", "--input", input_file
        )
        self.assertTrue(index.exists())
        self.assertEqual(0, len(jloadfile(index)[JsonConstants.REMOTE_PACKAGES]))

        with input_file.open("a") as fp:
            fp.write("{0}\n".format(self.workspace_folder / "a.leaf"))
        self.leaf_exec(
            ("build", "index"), "--resolve", "--output", index, "--name", "Name", "--description", "Description here", "--prettyprint", "--input", input_file
        )
        self.assertEqual(1, len(jloadfile(index)[JsonConstants.REMOTE_PACKAGES]))

        with input_file.open("a") as fp:
            fp.write(" ##  {0}  \n".format(self.workspace_folder / "b.leaf"))
        self.leaf_exec(
            ("build", "index"), "--resolve", "--output", index, "--name", "Name", "--description", "Description here", "--prettyprint", "--input", input_file
        )
        self.assertEqual(1, len(jloadfile(index)[JsonConstants.REMOTE_PACKAGES]))

        with input_file.open("a") as fp:
            fp.write("  {0}  \n".format(self.workspace_folder / "b.leaf"))
        self.leaf_exec(
            ("build", "index"), "--resolve", "--output", index, "--name", "Name", "--description", "Description here", "--prettyprint", "--input", input_file
        )
        self.assertEqual(2, len(jloadfile(index)[JsonConstants.REMOTE_PACKAGES]))

    def test_index_generation_with_non_relative_file(self):
        index = self.workspace_folder / "index.json"
        index2 = self.workspace_folder.parent / "index.json"

        aleaf = self.workspace_folder / "a.leaf"
        bleaf = self.workspace_folder.parent / "b.leaf"
        # Build some packages
        self.leaf_exec(("build", "pack"), "--output", aleaf, "--input", TEST_REMOTE_PACKAGE_SOURCE / "install_1.0")
        self.leaf_exec(("build", "pack"), "--output", bleaf, "--input", TEST_REMOTE_PACKAGE_SOURCE / "condition_1.0")

        self.leaf_exec(("build", "index"), "--output", index, aleaf, bleaf, expected_rc=2)
        self.leaf_exec(("build", "index"), "--resolve", "--output", index, aleaf, bleaf, expected_rc=2)
        self.leaf_exec(("build", "index"), "--output", index2, aleaf, bleaf)
        self.leaf_exec(("build", "index"), "--resolve", "--output", index2, aleaf, bleaf)

    def test_index_generation_with_extra_tags(self):
        index1 = self.workspace_folder / "index1.json"
        index2 = self.workspace_folder / "index2.json"
        folder = TEST_REMOTE_PACKAGE_SOURCE / "container-A_1.0"
        leaf_file = self.workspace_folder / "a.leaf"
        tags_file = self.workspace_folder / "a.leaf.tags"

        with tags_file.open("w") as fp:
            fp.write("foo\n")
            fp.write("bar\n")
            fp.write("  foo  \n")
            fp.write("  bar  \n")
            fp.write("\n")
            fp.write("   \n")
            fp.write("foo\n")
            fp.write("  hello\n")
            fp.write("bar\n")
            fp.write("world  \n")

        # Build some packages
        self.leaf_exec(("build", "pack"), "--output", leaf_file, "--input", folder)

        self.leaf_exec(("build", "index"), "--resolve", "--output", index1, "--prettyprint", leaf_file)
        self.assertTrue(index1.exists())
        self.leaf_exec(("build", "index"), "--resolve", "--output", index2, "--no-extra-tags", "--prettyprint", leaf_file)
        self.assertTrue(index2.exists())

        self.assertEqual(1, len(jloadfile(index1)[JsonConstants.REMOTE_PACKAGES]))
        self.assertEqual(1, len(jloadfile(index2)[JsonConstants.REMOTE_PACKAGES]))

        self.assertEqual(["foo", "bar", "hello", "world"], jloadfile(index1)[JsonConstants.REMOTE_PACKAGES][0]["info"]["tags"])
        self.assertEqual(["foo"], jloadfile(index2)[JsonConstants.REMOTE_PACKAGES][0]["info"]["tags"])

    def test_reproductible_build(self):
        # Build some packages
        pis = "install_1.0"
        folder = TEST_REMOTE_PACKAGE_SOURCE / pis
        manifest = folder / LeafFiles.MANIFEST
        self.assertTrue(manifest.exists())

        def touch_manifest():
            time.sleep(1)
            os.utime(str(manifest), None)

        def build_package(output, args):
            self.leaf_exec(("build", "pack"), "-i", folder, "-o", output, "--no-info", "--", *args)

        for extension, arg, mime in (("tar", "-v", "x-tar"), ("bz2", "-j", "x-bzip2"), ("xz", "-J", "x-xz")):
            output1 = self.workspace_folder / "{pis}.{ext}.{item}".format(pis=pis, ext=extension, item=1)
            output2 = self.workspace_folder / "{pis}.{ext}.{item}".format(pis=pis, ext=extension, item=2)
            output3 = self.workspace_folder / "{pis}.{ext}.{item}".format(pis=pis, ext=extension, item=3)
            output4 = self.workspace_folder / "{pis}.{ext}.{item}".format(pis=pis, ext=extension, item=4)

            build_package(output1, (arg, "."))
            touch_manifest()
            build_package(output2, (arg, "."))
            touch_manifest()
            build_package(output3, ("--mtime=2018-11-01 00:00:00", "--sort=name", "--owner=0", "--group=0", "--numeric-owner", arg, "."))
            touch_manifest()
            build_package(output4, ("--mtime=2018-11-01 00:00:00", "--sort=name", "--owner=0", "--group=0", "--numeric-owner", arg, "."))

            check_mime(output1, mime)
            check_mime(output2, mime)
            check_mime(output3, mime)
            check_mime(output4, mime)

            self.assertNotEqual(hash_compute(output1), hash_compute(output2))
            self.assertNotEqual(hash_compute(output1), hash_compute(output3))
            self.assertNotEqual(hash_compute(output2), hash_compute(output3))
            self.assertEqual(hash_compute(output3), hash_compute(output4))

    def test_package_custom_content(self):
        folder = TEST_REMOTE_PACKAGE_SOURCE / "install_1.0"
        artifact1 = self.workspace_folder / "a.leaf"
        artifact2 = self.workspace_folder / "b.leaf"
        self.leaf_exec(
            ("build", "pack"),
            "--no-info",
            "--output",
            artifact1,
            "--input",
            folder,
            "--",
            "--mtime=2018-11-01 00:00:00",
            "--sort=name",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "-J",
            ".",
        )

        self.leaf_exec(
            ("build", "pack"),
            "--no-info",
            "--output",
            artifact2,
            "--input",
            folder,
            "--",
            "--mtime=2018-11-01 00:00:00",
            "--sort=name",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "-J",
            "manifest.json",
        )

        self.assertGreater(artifact1.stat().st_size, artifact2.stat().st_size)

        # Error cases
        self.leaf_exec(("build", "pack"), "--no-info", "--output", self.workspace_folder / "error.leaf", "--input", folder, "--", "-v", expected_rc=2)


class TestCliRelengManagerVerbose(TestCliRelengManager):
    def __init__(self, *args, **kwargs):
        TestCliRelengManager.__init__(self, *args, verbosity="verbose", **kwargs)


class TestCliRelengManagerQuiet(TestCliRelengManager):
    def __init__(self, *args, **kwargs):
        TestCliRelengManager.__init__(self, *args, verbosity="quiet", **kwargs)
