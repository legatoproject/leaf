"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os

from tests.testutils import LeafTestCaseWithCli


class TestCliEntrypoints(LeafTestCaseWithCli):
    def test_list(self):
        self.leaf_exec(("package", "install"), "scripts_1.0")

        with self.assertStdout(template_out="list.out"):
            self.leaf_exec("run")
        with self.assertStdout(template_out="list-oneline.out"):
            self.leaf_exec("run", "--oneline")

    def test_run(self):
        self.leaf_exec(("package", "install"), "scripts_1.0")
        self.leaf_exec("run", "env")
        self.leaf_exec("run", "echo", "hello", "world")

        def check_file_creation(*args, rc=0):
            file = self.workspace_folder / "myfile.test"
            self.assertFalse(file.exists())
            args = list(args)
            args.append(file)
            self.leaf_exec("run", *args, expected_rc=rc)
            if rc == 0:
                self.assertTrue(file.exists())
                file.unlink()
            else:
                self.assertFalse(file.exists())

        check_file_creation("touch")
        check_file_creation("mytouch", rc=2)
        check_file_creation("-p", "scripts_1.0", "mytouch", rc=2)
        check_file_creation("-p", "subscripts_1.0", "mytouch")
        check_file_creation("--package", "subscripts_1.0", "mytouch")
        check_file_creation("--package", "subscripts_latest", "mytouch")
        check_file_creation("mytouch2")

    def test_latest(self):
        self.leaf_exec(("package", "install"), "scripts_1.0", "subscripts_latest")

        file = self.workspace_folder / "out.txt"

        def check_version(v):
            with file.open() as fp:
                self.assertEqual(["my special binary v{version}\n".format(version=v)], fp.readlines())

        self.leaf_exec("run", "-p", "subscripts_1.0", "mybin", file)
        check_version("1.0")

        self.leaf_exec("run", "-p", "subscripts_1.1", "mybin", file)
        check_version("1.1")

        self.leaf_exec("run", "-p", "subscripts_latest", "mybin", file)
        check_version("1.1")

        self.leaf_exec("run", "-p", "scripts_1.0", "mybin", file)
        check_version("1.0")

        self.leaf_exec("run", "-p", "scripts_latest", "mybin", file)
        check_version("1.0")

        self.leaf_exec("run", "mybin", file)
        check_version("1.1")

    def test_variables(self):
        self.leaf_exec(("package", "install"), "scripts_1.0")

        self.leaf_exec("run", "foo", expected_rc=42)

        file = self.workspace_folder / "out.txt"
        self.leaf_exec("env", "user", "--set", "MY_CUSTOM_VAR2=Hello")
        self.leaf_exec("env", "user", "--set", "MY_CUSTOM_VAR3=$MY_CUSTOM_VAR2 World")

        variables = {"{LANG}": os.getenv("LANG"), "{file}": file}

        tests = {
            ("foo", file, " hello world ", " $LEAF_VERSION "): "fooshell.file",
            ("foo", "-p", "scripts_1.0", file, " hello world ", " $LEAF_VERSION "): "fooshell2.file",
        }
        for command, template_name in tests.items():
            if file.exists():
                file.unlink()
            self.assertFalse(file.exists())
            self.leaf_exec("run", *command)
            self.assertTrue(file.exists())
            self.assertFileContentEquals(file, template_name, variables=variables)
