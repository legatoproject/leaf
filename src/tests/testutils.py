import platform
import subprocess
import sys
import unittest
from builtins import ValueError, reversed
from collections import OrderedDict
from pathlib import Path
from tempfile import mkdtemp
from unittest.case import TestCase

from _io import StringIO
from leaf import __version__
from leaf.__main__ import run_leaf
from leaf.api import RelengManager
from leaf.core.constants import JsonConstants, LeafFiles, LeafSettings
from leaf.core.jsonutils import jloadfile, jwritefile
from leaf.core.settings import EnvVar
from leaf.core.utils import mkdirs, rmtree_force
from leaf.model.environment import Environment
from leaf.model.package import Manifest, PackageIdentifier

LeafSettings.NON_INTERACTIVE.value = 1

TestCase.maxDiff = None
LEAF_UT_DEBUG = EnvVar("LEAF_UT_DEBUG")
LEAF_UT_SKIP = EnvVar("LEAF_UT_SKIP", "")
LEAF_UT_CREATE_TEMPLATE = EnvVar("LEAF_UT_CREATE_TEMPLATE")

LEAF_PROJECT_ROOT_FOLDER = Path(__file__).parent.parent.parent

LEAF_SYSTEM_ROOT = LEAF_PROJECT_ROOT_FOLDER / "resources" / "share" / "leaf" / "packages"
TEST_RESOURCES_FOLDER = LEAF_PROJECT_ROOT_FOLDER / "src" / "tests" / "resources"
TEST_REMOTE_PACKAGE_SOURCE = TEST_RESOURCES_FOLDER / "packages"
TEST_LEAF_SYSTEM_ROOT = TEST_RESOURCES_FOLDER / "system_packages"
TEST_GPG_HOMEDIR = TEST_RESOURCES_FOLDER / "gpg"


TAR_EXTRA_ARGS = {
    PackageIdentifier.parse("compress-xz_1.0"): ("-z", "."),
    PackageIdentifier.parse("compress-bz2_1.0"): ("-j", "."),
    PackageIdentifier.parse("compress-gz_1.0"): ("-J", "."),
}
ALT_INDEX_CONTENT = {"multitags_1.0": True, "version_2.0": False, "upgrade_1.2": False, "upgrade_2.0": False}
TEST_GPG_FINGERPRINT = "E35D6817397359074160F68952ECE808A2BC372C"


class StringIOWrapper(StringIO):
    def __init__(self, stream, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.__altstream__ = stream

    def write(self, txt):
        super().write(txt)
        self.__altstream__.write(txt)

    @property
    def encoding(self):
        return self.__altstream__.encoding

    @encoding.setter
    def encoding(self, enc):
        self.__altstream__.encoding = enc


class ContentChecker:
    def __init__(self, tester, expected_out=None, expected_err=None, variables=None):
        self.tester = tester
        self.variables = variables
        self.expected_out, self.expected_err = expected_out, expected_err
        self.sysstdout, self.sysstderr = sys.stdout, sys.stderr
        self.stdout_wrapper, self.stderr_wrapper = StringIOWrapper(self.sysstdout), StringIOWrapper(self.sysstderr)

    def __enter__(self):
        sys.stdout, sys.stderr = self.stdout_wrapper, self.stderr_wrapper

    def __exit__(self, *_):
        sys.stdout, sys.stderr = self.sysstdout, self.sysstderr
        check_content(self.tester, self.expected_out, self.stdout_wrapper.getvalue().splitlines(), self.variables)
        check_content(self.tester, self.expected_err, self.stderr_wrapper.getvalue().splitlines(), self.variables)


class LeafTestCase(unittest.TestCase):

    _TEST_FOLDER = None

    @classmethod
    def setUpClass(cls):
        # Setup test folder for this class
        LeafTestCase._TEST_FOLDER = Path(mkdtemp(prefix="leaf_tests_"))
        assert TEST_RESOURCES_FOLDER.exists(), "Cannot find resources folder!"

    @classmethod
    def tearDownClass(cls):
        # Do not remove folder in case of debug
        if not LEAF_UT_DEBUG.as_boolean():
            rmtree_force(LeafTestCase._TEST_FOLDER)

    def __init__(self, *args, verbosity=None, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
        self.__verbosity = verbosity

    @property
    def verbosity(self):
        return self.__verbosity

    @property
    def test_folder(self):
        return mkdirs(LeafTestCase._TEST_FOLDER)

    @property
    def volatile_folder(self):
        return mkdirs(self.test_folder / "volatile")

    @property
    def config_folder(self):
        return mkdirs(self.volatile_folder / "config")

    @property
    def cache_folder(self):
        return mkdirs(self.volatile_folder / "cache")

    @property
    def install_folder(self):
        return mkdirs(self.volatile_folder / "packages")

    @property
    def workspace_folder(self):
        return mkdirs(self.volatile_folder / "workspace")

    @property
    def alt_workspace_folder(self):
        return mkdirs(self.volatile_folder / "alt-workspace")

    def setUp(self):
        if self.verbosity and LEAF_UT_SKIP.is_set():
            if self.verbosity.lower() in LEAF_UT_SKIP.value.lower():
                self.skipTest("Verbosity {verbosity} is ignored".format(verbosity=self.verbosity))

        # Clean volatile folder just in case
        rmtree_force(self.volatile_folder)
        # Setup leaf via env
        LeafSettings.VERBOSITY.value = self.verbosity
        LeafSettings.CONFIG_FOLDER.value = self.config_folder
        LeafSettings.CACHE_FOLDER.value = self.cache_folder
        LeafSettings.USER_PKG_FOLDER.value = self.install_folder

    def tearDown(self):
        # Reset env
        LeafSettings.VERBOSITY.value = None
        LeafSettings.CONFIG_FOLDER.value = None
        LeafSettings.CACHE_FOLDER.value = None
        LeafSettings.USER_PKG_FOLDER.value = None
        # Clean volatile folder
        rmtree_force(self.volatile_folder)

    def _get_default_variables(self):
        out = OrderedDict()
        out["{TESTS_LEAF_VERSION}"] = __version__
        out["{TESTS_PLATFORM_SYSTEM}"] = platform.system()
        out["{TESTS_PLATFORM_MACHINE}"] = platform.machine()
        out["{TESTS_PLATFORM_RELEASE}"] = platform.release()
        out["{LEAF_PROJECT_ROOT_FOLDER}"] = LEAF_PROJECT_ROOT_FOLDER
        out["{TESTS_FOLDER}"] = self.test_folder
        return out

    def assertFileContentEquals(self, actual_file: Path, template_name: str, variables: dict = None):  # noqa: N802
        content_variables = self._get_default_variables()
        if variables is not None:
            content_variables.update(variables)
        check_content(self, self.get_template_file(template_name), get_lines(actual_file), content_variables)

    def get_template_file(self, template_name):
        # Template is a file name
        self.assertTrue(isinstance(template_name, str))
        class_folder = TEST_RESOURCES_FOLDER / "expected_ouput" / self.__class__.__name__
        template = self.id().split(".")[-1] + "_" + template_name
        return class_folder / template

    def assertStdout(self, template_out=None, template_err=None, variables: dict = None):  # noqa: N802
        """
        Possibles values for templates :
        - None -> the stream is not checked
        - Empty list, tuple or set -> the stream is checked as empty
        - File name -> the stream is compared to the file content
        """
        content_variables = self._get_default_variables()
        if variables is not None:
            content_variables.update(variables)
        return ContentChecker(
            self,
            expected_out=self.get_template_file(template_out) if template_out else None,
            expected_err=self.get_template_file(template_err) if template_err else None,
            variables=content_variables,
        )


class LeafTestCaseWithRepo(LeafTestCase):
    @classmethod
    def setUpClass(cls):
        LeafTestCase.setUpClass()
        generate_repository(TEST_REMOTE_PACKAGE_SOURCE, LeafTestCaseWithRepo._TEST_FOLDER / "repository")

    @property
    def repository_folder(self):
        return mkdirs(self.test_folder / "repository")

    @property
    def remote_url1(self):
        return (self.repository_folder / "index.json").as_uri()

    @property
    def remote_url2(self):
        return str(self.repository_folder / "index2.json")

    def _get_default_variables(self):
        out = super()._get_default_variables()
        out["{TESTS_REMOTE_URL}"] = self.remote_url1
        out["{TESTS_REMOTE_URL2}"] = self.remote_url2
        return out

    def check_content(self, content, pislist):
        self.assertEqual(len(content), len(pislist))
        for pis in pislist:
            self.assertTrue(PackageIdentifier.parse(pis) in content)

    def check_installed_packages(self, pislist, install_folder=None):
        if install_folder is None:
            install_folder = self.install_folder

        for pis in pislist:
            folder = install_folder / str(pis)
            self.assertTrue(folder.is_dir(), msg=str(folder))
        count = 0
        for i in install_folder.iterdir():
            if i.is_dir():
                count += 1
        self.assertEqual(len(pislist), count)

    def check_current_profile(self, name):
        lnk = self.workspace_folder / LeafFiles.WS_DATA_FOLDERNAME / LeafFiles.CURRENT_PROFILE_LINKNAME
        if name is None:
            self.assertFalse(lnk.exists())
        else:
            self.assertEqual(name, lnk.resolve().name)

    def check_profile_content(self, name, content):
        folder = self.workspace_folder / LeafFiles.WS_DATA_FOLDERNAME / name
        if content is None:
            self.assertFalse(folder.exists())
        else:
            self.assertTrue(folder.exists())
            symlink_count = 0
            for item in folder.iterdir():
                if item.is_symlink():
                    symlink_count += 1
                self.assertTrue(item.name in content, "Unexpected link {link}".format(link=item))
            self.assertEqual(symlink_count, len(content))


class LeafTestCaseWithCli(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()
        LeafSettings.SYSTEM_PKG_FOLDERS.value = ""
        self.leaf_exec(("remote", "add"), "default", self.remote_url1)
        self.leaf_exec(("remote", "add"), "other", self.remote_url2)

    def tearDown(self):
        super().tearDown()
        LeafSettings.SYSTEM_PKG_FOLDERS.value = None

    def simple_exec(self, *command, bin="leaf", expected_rc=0, silent=True):
        cmd = " ".join(map(str, command))
        if bin is not None:
            cmd = bin + " " + cmd
        # Mask verbosity if set
        oldverbosity = LeafSettings.VERBOSITY.value
        try:
            LeafSettings.VERBOSITY.value = None
            rc, stdout = subprocess.getstatusoutput(cmd)
            if not silent and stdout:
                print(stdout)
            if expected_rc is not None:
                self.assertEqual(expected_rc, rc)
            return stdout
        finally:
            LeafSettings.VERBOSITY.value = oldverbosity

    def leaf_exec(self, verb, *args, alt_ws=None, expected_rc=0):
        if alt_ws is None:
            alt_ws = self.workspace_folder

        command = []
        if self.verbosity == "quiet":
            command.append("--quiet")
        elif self.verbosity == "verbose":
            command.append("--verbose")
        command += ("--non-interactive", "--workspace", alt_ws)
        if isinstance(verb, (list, tuple)):
            command += verb
        else:
            command.append(verb)
        if args is not None:
            command += args
        self.__execute(command, expected_rc)

    def __execute(self, command, expected_rc):
        command = [str(i) for i in command]
        # Mask verbosity if set
        oldverbosity = LeafSettings.VERBOSITY.value
        try:
            LeafSettings.VERBOSITY.value = None
            out = run_leaf(command, catch_int_sig=False)
            if expected_rc is not None:
                self.assertEqual(expected_rc, out, " ".join(command))
            return out
        finally:
            LeafSettings.VERBOSITY.value = oldverbosity


def get_lines(file):
    with file.open() as fp:
        return fp.read().splitlines()


def env_file_to_map(dump_file):
    out = {}
    for line in get_lines(dump_file):
        i = line.index("=")
        out[line[:i]] = line[i + 1 :]
    return out


def generate_repository(source_folder, output_folder):

    mkdirs(output_folder)

    artifacts_list1 = []
    artifacts_list2 = []

    rm = RelengManager()
    for package_folder in source_folder.iterdir():
        if package_folder.is_dir() and PackageIdentifier.is_valid_identifier(package_folder.name):
            manifest_file = package_folder / LeafFiles.MANIFEST
            if manifest_file.is_file():
                manifest = Manifest.parse(manifest_file)
                if str(manifest.identifier) != package_folder.name:
                    raise ValueError("Naming error: {mf.identifier} != {folder.name}".format(mf=manifest, folder=package_folder))
                filename = str(manifest.identifier) + ".leaf"
                output_file = output_folder / filename
                tar_extraargs = TAR_EXTRA_ARGS.get(manifest.identifier)
                rm.create_package(package_folder, output_file, tar_extra_args=tar_extraargs)
                # Check that the generated archive is OK
                check_archive_format(output_file, tar_extraargs[0] if tar_extraargs is not None else None)
                # Create multi index.json
                if str(manifest.identifier) in ALT_INDEX_CONTENT:
                    artifacts_list2.append(output_file)
                    if ALT_INDEX_CONTENT[str(manifest.identifier)]:
                        artifacts_list1.append(output_file)
                else:
                    artifacts_list1.append(output_file)
                # Create a problem with failure-badhash package
                if manifest.name == "failure-badhash":
                    info_node = jloadfile(rm.find_external_info_file(output_file))
                    # chosen by fair dice roll.
                    # garanteed to be random.
                    info_node[
                        JsonConstants.REMOTE_PACKAGE_HASH
                    ] = "sha384:d1083143b5c4cf7f1ddaadc391b2d0102fc9fffeb0951ec51020b512ef9548d40cd1af079a1221133faa949fdc304c41"
                    jwritefile(rm.find_external_info_file(output_file), info_node, pp=True)

    if len(artifacts_list1) == 0 or len(artifacts_list2) == 0:
        raise ValueError("Empty index!")

    with (output_folder / "multitags_1.0.leaf.tags").open("w") as fp:
        fp.write("volatileTag1\n")
        fp.write("volatileTag2")
    rm.generate_index(output_folder / "index.json", artifacts_list1, name="First repository", description="First repository description", prettyprint=True)

    with (output_folder / "multitags_1.0.leaf.tags").open("w") as fp:
        fp.write("volatileTag3\n")
        fp.write("volatileTag4")
    rm.generate_index(output_folder / "index2.json", artifacts_list2, name="Second repository", description="Second repository description", prettyprint=True)

    # Alter some values for test purpose
    index1json = jloadfile(output_folder / "index.json")
    for pkgjson in index1json[JsonConstants.REMOTE_PACKAGES]:
        if pkgjson["info"]["name"] == "failure-large-ap":
            pkgjson["size"] = 999999999999
    jwritefile(output_folder / "index.json", index1json, pp=True)

    # Sign with GPG
    subprocess.check_call(["gpg", "--homedir", str(TEST_GPG_HOMEDIR), "--detach-sign", "--armor", str(output_folder / "index.json")])
    subprocess.check_call(["gpg", "--homedir", str(TEST_GPG_HOMEDIR), "--detach-sign", "--armor", str(output_folder / "index2.json")])


def check_archive_format(file, compression):
    if compression == "-J":
        check_mime(file, "x-xz")
    elif compression == "-z":
        check_mime(file, "gzip")
    elif compression == "-j":
        check_mime(file, "x-bzip2")
    else:
        check_mime(file, "x-tar")


def check_mime(file, expected_mime, support_legacy=True):
    mime = subprocess.getoutput("file -bi " + str(file))
    accepted_types = [expected_mime]
    if support_legacy and not expected_mime.startswith("x-"):
        # Handle case x-MIME for legacy types like gzip
        accepted_types.append("x-" + expected_mime)

    for t in accepted_types:
        if mime.startswith("application/" + t):
            return
    raise ValueError("File {file} has invalid mime type {mime}".format(file=file, mime=mime))


def env_tolist(env: Environment):
    out = []
    env.activate(kv_consumer=lambda k, v: out.append((k, v)))
    return out


def replace_vars(line: str, variables: dict, reverse: bool = False):
    if variables:
        for k in reversed(variables.keys()) if reverse else variables.keys():
            v = str(variables[k])
            k = str(k)
            if reverse:
                line = line.replace(v, k)
            else:
                line = line.replace(k, v)
    return line


def check_content(tester: TestCase, template_file: Path, lines: list, variables: dict):
    if template_file is None:
        # No check
        return

    if LEAF_UT_CREATE_TEMPLATE.as_boolean():
        # Generate template if envar is set
        if not template_file.parent.exists():
            template_file.parent.mkdir()
        with template_file.open("w") as fp:
            for line in lines:
                fp.write(replace_vars(line, variables, reverse=True) + "\n")

    # Check content with actual content
    template_lines = list(map(lambda l: replace_vars(l, variables, reverse=False), get_lines(template_file)))
    tester.assertEqual(lines, template_lines)


if __name__ == "__main__":
    output = Path("/tmp/leaf/repository")
    print("Generate repository in {output}".format(output=output))
    rmtree_force(output)
    mkdirs(output)
    generate_repository(TEST_REMOTE_PACKAGE_SOURCE, output)
