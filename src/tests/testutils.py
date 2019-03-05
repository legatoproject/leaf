import shutil
import subprocess
import sys
import unittest
import platform
from builtins import ValueError
from pathlib import Path
from tempfile import mkdtemp
from unittest.case import TestCase

from _io import StringIO
from leaf import __version__
from leaf.__main__ import run_leaf
from leaf.api import RelengManager
from leaf.core.constants import JsonConstants, LeafFiles, LeafSettings
from leaf.core.jsonutils import jloadfile, jwritefile
from leaf.core.settings import Setting
from leaf.model.package import Manifest, PackageIdentifier

LeafSettings.NON_INTERACTIVE.value = 1

TestCase.maxDiff = None
LEAF_UT_DEBUG = Setting("LEAF_UT_DEBUG")
LEAF_UT_SKIP = Setting("LEAF_UT_SKIP", "")
LEAF_UT_CREATE_TEMPLATE = Setting("LEAF_UT_CREATE_TEMPLATE")

PROJECT_ROOT_FOLDER = Path(__file__).parent.parent.parent
RESOURCE_FOLDER = PROJECT_ROOT_FOLDER / "src/tests/resources"
EXPECTED_OUTPUT_FOLDER = PROJECT_ROOT_FOLDER / "src/tests/expected_ouput"
PLUGINS_FOLDER = PROJECT_ROOT_FOLDER / "resources/share/leaf/plugins"

TAR_EXTRA_ARGS = {
    PackageIdentifier.parse("compress-xz_1.0"): ("-z", "."),
    PackageIdentifier.parse("compress-bz2_1.0"): ("-j", "."),
    PackageIdentifier.parse("compress-gz_1.0"): ("-J", "."),
}
ALT_INDEX_CONTENT = {"multitags_1.0": True, "version_2.0": False, "upgrade_1.2": False, "upgrade_2.0": False}

TEST_GPG_FINGERPRINT = "E35D6817397359074160F68952ECE808A2BC372C"
TEST_GPG_HOMEDIR = PROJECT_ROOT_FOLDER / "src/tests/gpg"


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
    def __init__(self, tester, testcase, template_out=None, template_err=(), variables=None):
        self.tester = tester
        self.testcase = testcase
        self.template_out, self.template_err = template_out, template_err
        self.variables = variables
        self.sysstdout = sys.stdout
        self.sysstderr = sys.stderr
        self.stdout_wrapper = StringIOWrapper(self.sysstdout)
        self.stderr_wrapper = StringIOWrapper(self.sysstderr)

    def __enter__(self):
        sys.stdout = self.stdout_wrapper
        sys.stderr = self.stderr_wrapper

    def __exit__(self, *_):
        sys.stdout = self.sysstdout
        sys.stderr = self.sysstderr
        self.__check_content(self.template_out, self.stdout_wrapper)
        self.__check_content(self.template_err, self.stderr_wrapper)

    def __check_content(self, template, stream):
        if template is None:
            # No check
            return

        stream_lines = stream.getvalue().splitlines()
        lines = []
        if isinstance(template, str):
            # Template is a file name
            class_folder = EXPECTED_OUTPUT_FOLDER / self.testcase.__class__.__name__
            template = self.testcase.id().split(".")[-1] + "_" + template
            template = class_folder / template

            # Generate template if envar is set
            if LEAF_UT_CREATE_TEMPLATE.as_boolean():
                if not class_folder.exists():
                    class_folder.mkdir()
                for line in stream_lines:
                    line = self.__replace_variables(line, True)
                    lines.append(line)
                with template.open(mode="w") as f:
                    f.write("\n".join(lines))
                return

            # Read template content
            self.tester.assertTrue(template.exists())
            with open(str(template)) as fp:
                for line in fp.read().splitlines():
                    line = self.__replace_variables(line)
                    lines.append(line)
        else:
            lines = template

        self.tester.assertEqual(lines, stream_lines)

    def __replace_variables(self, line, reverse=False):
        if self.variables is not None:
            for k, v in self.variables.items():
                k, v = str(k), str(v)
                if reverse:
                    line = line.replace(v, k)
                else:
                    line = line.replace(k, v)
        return line


class LeafTestCase(unittest.TestCase):
    def __init__(self, *args, verbosity=None, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
        self.__verbosity = verbosity

    @property
    def verbosity(self):
        return self.__verbosity

    def setUp(self):
        if self.__verbosity and LEAF_UT_SKIP.is_set():
            if self.__verbosity.lower() in LEAF_UT_SKIP.value.lower():
                self.skipTest("Verbosity {verbosity} is ignored".format(verbosity=self.__verbosity))

        print("[LEAF_VERBOSE]  {classname}  -->  {verbosity}".format(classname=self.__class__.__name__, verbosity=self.__verbosity))
        LeafSettings.VERBOSITY.value = self.__verbosity

    def _get_default_variables(self):
        return {
            "{TESTS_LEAF_VERSION}": __version__,
            "{TESTS_PLATFORM_SYSTEM}": platform.system(),
            "{TESTS_PLATFORM_MACHINE}": platform.machine(),
            "{TESTS_PLATFORM_RELEASE}": platform.release(),
            "{TESTS_PROJECT_FOLDER}": PROJECT_ROOT_FOLDER,
        }

    def assertStdout(self, template_out=None, template_err=[], variables=None):  # noqa: N802
        """
        Possibles values for templates :
        - None -> the stream is not checked
        - Empty list, tuple or set -> the stream is checked as empty
        - File name -> the stream is compared to the file content
        """
        content_variables = self._get_default_variables()
        if variables is not None:
            content_variables.update(variables)
        return ContentChecker(self, testcase=self, template_out=template_out, template_err=template_err, variables=content_variables)


class LeafTestCaseWithRepo(LeafTestCase):

    ROOT_FOLDER = None
    REPO_FOLDER = None
    VOLATILE_FOLDER = None

    @classmethod
    def setUpClass(cls):
        LeafTestCase.setUpClass()

        if LEAF_UT_DEBUG.as_boolean():
            LeafTestCaseWithRepo.ROOT_FOLDER = Path("/tmp/leaf")
        else:
            LeafTestCaseWithRepo.ROOT_FOLDER = Path(mkdtemp(prefix="leaf_tests_"))

        LeafTestCaseWithRepo.REPO_FOLDER = LeafTestCaseWithRepo.ROOT_FOLDER / "repository"
        LeafTestCaseWithRepo.VOLATILE_FOLDER = LeafTestCaseWithRepo.ROOT_FOLDER / "volatile"

        shutil.rmtree(str(LeafTestCaseWithRepo.ROOT_FOLDER), ignore_errors=True)

        assert RESOURCE_FOLDER.exists(), "Cannot find resources folder!"
        cls.__generate_repository(RESOURCE_FOLDER, LeafTestCaseWithRepo.REPO_FOLDER)

    @classmethod
    def tearDownClass(cls):
        if not LEAF_UT_DEBUG.as_boolean():
            shutil.rmtree(str(LeafTestCaseWithRepo.ROOT_FOLDER), True)

    @classmethod
    def __generate_repository(cls, source_folder, output_folder):
        if not output_folder.is_dir():
            output_folder.mkdir(parents=True)
        artifacts_list1 = []
        artifacts_list2 = []

        LeafSettings.VERBOSITY.value = "quiet"
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
                    cls.__check_archive_format(output_file, tar_extraargs[0] if tar_extraargs is not None else None)
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
        LeafSettings.VERBOSITY.value = None

        if len(artifacts_list1) == 0 or len(artifacts_list2) == 0:
            raise ValueError("Empty index!")

        with open(str(output_folder / "multitags_1.0.leaf.tags"), "w") as fp:
            fp.write("volatileTag1\n")
            fp.write("volatileTag2")
        rm.generate_index(output_folder / "index.json", artifacts_list1, name="First repository", description="First repository description", prettyprint=True)

        with open(str(output_folder / "multitags_1.0.leaf.tags"), "w") as fp:
            fp.write("volatileTag3\n")
            fp.write("volatileTag4")
        rm.generate_index(
            output_folder / "index2.json", artifacts_list2, name="Second repository", description="Second repository description", prettyprint=True
        )

        # Sign with GPG
        subprocess.check_call(["gpg", "--homedir", str(TEST_GPG_HOMEDIR), "--detach-sign", "--armor", str(output_folder / "index.json")])
        subprocess.check_call(["gpg", "--homedir", str(TEST_GPG_HOMEDIR), "--detach-sign", "--armor", str(output_folder / "index2.json")])

    @classmethod
    def __check_archive_format(cls, file, compression):
        if compression == "-J":
            check_mime(file, "x-xz")
        elif compression == "-z":
            check_mime(file, "gzip")
        elif compression == "-j":
            check_mime(file, "x-bzip2")
        else:
            check_mime(file, "x-tar")

    def _get_default_variables(self):
        out = super()._get_default_variables()
        out.update(
            {
                "{TESTS_WORKSPACE_FOLDER}": self.ws_folder,
                "{TESTS_REMOTE_URL}": self.remote_url1,
                "{TESTS_REMOTE_URL2}": self.remote_url2,
                "{TESTS_INSTALL_FOLDER}": self.install_folder,
                "{TESTS_CACHE_FOLDER}": self.cache_folder,
            }
        )
        return out

    def setUp(self):
        shutil.rmtree(str(LeafTestCaseWithRepo.VOLATILE_FOLDER), ignore_errors=True)
        LeafTestCaseWithRepo.VOLATILE_FOLDER.mkdir()
        LeafSettings.CONFIG_FOLDER.value = self.configuration_folder
        LeafSettings.CACHE_FOLDER.value = self.cache_folder

    def tearDown(self):
        pass

    @property
    def remote_url1(self):
        return (LeafTestCaseWithRepo.REPO_FOLDER / "index.json").as_uri()

    @property
    def remote_url2(self):
        return str(LeafTestCaseWithRepo.REPO_FOLDER / "index2.json")

    def __get_volatile_item(self, name, mkdir=True):
        out = LeafTestCaseWithRepo.VOLATILE_FOLDER / name
        if mkdir and not out.is_dir():
            out.mkdir()
        return out

    @property
    def configuration_folder(self):
        return self.__get_volatile_item("config", mkdir=True)

    @property
    def install_folder(self):
        return self.__get_volatile_item("packages")

    @property
    def cache_folder(self):
        return self.__get_volatile_item("cache", mkdir=True)

    @property
    def ws_folder(self):
        return self.__get_volatile_item("workspace")

    @property
    def alt_ws_folder(self):
        return self.__get_volatile_item("alt-workspace")

    def check_content(self, content, pislist):
        self.assertEqual(len(content), len(pislist))
        for pis in pislist:
            self.assertTrue(PackageIdentifier.parse(pis) in content)

    def check_installed_packages(self, pislist):
        for pis in pislist:
            folder = self.install_folder / str(pis)
            self.assertTrue(folder.is_dir(), msg=str(folder))
        count = 0
        for i in self.install_folder.iterdir():
            if i.is_dir():
                count += 1
        self.assertEqual(len(pislist), count)

    def check_current_profile(self, name):
        lnk = self.ws_folder / LeafFiles.WS_DATA_FOLDERNAME / LeafFiles.CURRENT_PROFILE_LINKNAME
        if name is None:
            self.assertFalse(lnk.exists())
        else:
            self.assertEqual(name, lnk.resolve().name)

    def check_profile_content(self, name, content):
        folder = self.ws_folder / LeafFiles.WS_DATA_FOLDERNAME / name
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
    @classmethod
    def setUpClass(cls):
        LeafTestCaseWithRepo.setUpClass()
        LeafSettings.RESOURCES_FOLDER.value = PLUGINS_FOLDER.parent

    @classmethod
    def tearDownClass(cls):
        LeafTestCaseWithRepo.tearDownClass()

    def _get_default_variables(self):
        out = super()._get_default_variables()
        out.update({"{TESTS_RESOURCES_FOLDER}": LeafSettings.RESOURCES_FOLDER.value})
        return out

    def setUp(self):
        LeafTestCaseWithRepo.setUp(self)
        self.leaf_exec("config", "--root", self.install_folder)
        self.leaf_exec(("remote", "add"), "--insecure", "default", self.remote_url1)
        self.leaf_exec(("remote", "add"), "--insecure", "other", self.remote_url2)

    def simple_exec(self, *command, bin="leaf", expected_rc=0):
        cmd = " ".join(command)
        if bin is not None:
            cmd = bin + " " + cmd
        # Mask verbosity if set
        oldverbosity = LeafSettings.VERBOSITY.value
        try:
            LeafSettings.VERBOSITY.value = None
            rc, stdout = subprocess.getstatusoutput(cmd)
            if expected_rc is not None:
                self.assertEqual(expected_rc, rc)
            return stdout
        finally:
            LeafSettings.VERBOSITY.value = oldverbosity

    def leaf_exec(self, verb, *args, alt_ws=None, expected_rc=0):
        if alt_ws is None:
            alt_ws = self.ws_folder

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


def check_mime(file, expected_mime):
    mime = subprocess.getoutput("file -bi " + str(file))
    if not mime.startswith("application/" + expected_mime):
        raise ValueError("File {file} has invalid mime type {mime}".format(file=file, mime=mime))


def get_lines(file):
    with file.open() as fp:
        return fp.read().splitlines()


def env_file_to_map(dump_file):
    out = {}
    for line in get_lines(dump_file):
        i = line.index("=")
        out[line[:i]] = line[i + 1 :]
    return out
