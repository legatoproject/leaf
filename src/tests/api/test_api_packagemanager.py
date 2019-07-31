"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os
import random
import socketserver
import sys
import time
import unittest
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler
from multiprocessing import Process
from time import sleep

from leaf.api import PackageManager
from leaf.core.error import (
    InvalidHashException,
    InvalidPackageNameException,
    LeafOutOfDateException,
    NoEnabledRemoteException,
    NoRemoteException,
    PrereqException,
)
from leaf.core.settings import EnvVar
from leaf.core.utils import NotEnoughSpaceException, is_folder_ignored
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import AvailablePackage, InstalledPackage, LeafArtifact, PackageIdentifier
from tests.testutils import ALT_INDEX_CONTENT, LEAF_UT_SKIP, LeafTestCaseWithRepo, env_tolist, get_lines

HTTP_PORT = EnvVar("LEAF_HTTP_PORT", random.randint(54000, 54999))

# Needed for http server
sys.path.insert(0, os.path.abspath("../.."))


class TestApiPackageManager(LeafTestCaseWithRepo):
    def setUp(self):
        super().setUp()

        self.pm = PackageManager()

        with self.assertRaises(NoRemoteException):
            self.pm.list_available_packages()
        self.assertEqual(0, len(self.pm.list_installed_packages()))
        with self.assertRaises(NoRemoteException):
            self.pm.list_remotes()
        self.assertEqual(0, len(self.pm.read_user_configuration().remotes))

        self.pm.create_remote("default", self.remote_url1, insecure=True)
        self.pm.create_remote("other", self.remote_url2, insecure=True)
        self.assertEqual(2, len(self.pm.read_user_configuration().remotes))
        self.pm.fetch_remotes(True)
        self.assertEqual(2, len(self.pm.list_remotes()))
        self.assertTrue(self.pm.list_remotes()["default"].is_fetched)
        self.assertTrue(self.pm.list_remotes()["other"].is_fetched)
        self.assertNotEqual(0, len(self.pm.list_available_packages()))

    def test_compression(self):
        pislist = ["compress-bz2_1.0", "compress-gz_1.0", "compress-tar_1.0", "compress-xz_1.0"]
        self.pm.install_packages(PackageIdentifier.parse_list(pislist))
        self.check_content(self.pm.list_installed_packages(), pislist)

    def test_enable_disable_remote(self):
        self.assertEqual(2, len(self.pm.list_remotes(True)))
        self.assertTrue(len(self.pm.list_available_packages()) > 0)

        remote = self.pm.list_remotes()["default"]
        remote.enabled = False
        self.pm.update_remote(remote)
        self.assertEqual(2, len(self.pm.list_remotes(False)))
        self.assertEqual(1, len(self.pm.list_remotes(True)))
        self.assertEqual(len(ALT_INDEX_CONTENT), len(self.pm.list_available_packages()))

        remote = self.pm.list_remotes()["other"]
        remote.enabled = False
        self.pm.update_remote(remote)
        self.assertEqual(2, len(self.pm.list_remotes(False)))
        with self.assertRaises(NoEnabledRemoteException):
            self.pm.list_remotes(True)
        with self.assertRaises(NoEnabledRemoteException):
            self.pm.list_available_packages()

        remote = self.pm.list_remotes()["default"]
        remote.enabled = True
        self.pm.update_remote(remote)
        remote = self.pm.list_remotes()["other"]
        remote.enabled = True
        self.pm.update_remote(remote)
        self.assertEqual(2, len(self.pm.list_remotes(False)))
        self.assertEqual(2, len(self.pm.list_remotes(True)))
        self.assertTrue(len(self.pm.list_available_packages()) > 0)

    def test_container(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0"])

        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_2.0"]))
        self.check_content(
            self.pm.list_installed_packages(),
            ["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0", "container-A_2.0", "container-D_1.0"],
        )

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["container-A_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["container-A_2.0", "container-C_1.0", "container-D_1.0"])

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["container-A_2.0"]))
        self.check_content(self.pm.list_installed_packages(), [])

    def test_install_unknown_package(self):
        with self.assertRaises(InvalidPackageNameException):
            self.pm.install_packages(PackageIdentifier.parse_list(["unknwonPackage"]))
        with self.assertRaises(InvalidPackageNameException):
            self.pm.install_packages(PackageIdentifier.parse_list(["container-A"]))
        with self.assertRaises(InvalidPackageNameException):
            self.pm.install_packages(PackageIdentifier.parse_list(["unknwonPackage_1.0"]))

    def test_bad_container(self):
        with self.assertRaises(Exception):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-depends-leaf_1.0"]))
        self.check_content(self.pm.list_installed_packages(), [])

    def test_container_not_master(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_1.1"]))
        self.check_content(self.pm.list_installed_packages(), ["container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0"])

        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        self.check_content(
            self.pm.list_installed_packages(),
            ["container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0", "container-A_2.1", "container-D_1.0"],
        )

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["container-A_1.1"]))
        self.check_content(self.pm.list_installed_packages(), ["container-A_2.1", "container-C_1.0", "container-D_1.0"])

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["container-A_2.1"]))
        self.check_content(self.pm.list_installed_packages(), [])

    def test_steps(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["install_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["install_1.0"])

        folder = self.install_folder / "install_1.0"

        self.assertTrue(folder.is_dir())
        self.assertTrue((folder / "data1").is_file())
        self.assertTrue((folder / "folder").is_dir())
        self.assertTrue((folder / "folder" / "data2").is_file())
        self.assertTrue((folder / "folder" / "data1-symlink").is_symlink())

        self.assertFalse((self.install_folder / "uninstall.log").is_file())
        self.assertTrue((folder / "postinstall.log").is_file())
        self.assertTrue((folder / "targetFileFromEnv").is_file())
        self.assertTrue((folder / "dump.env").is_file())
        self.assertTrue((folder / "folder2").is_dir())
        with (folder / "targetFileFromEnv").open() as fp:
            content = fp.read().splitlines()
            self.assertEqual(1, len(content))
            self.assertEqual(str(folder), content[0])

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["install_1.0"]))
        self.check_content(self.pm.list_installed_packages(), [])
        self.assertTrue((self.install_folder / "uninstall.log").is_file())

    def test_postinstall_error(self):
        with self.assertRaises(Exception):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-postinstall-exec_1.0"]), keep_folder_on_error=True)
        found = False
        for folder in self.install_folder.iterdir():
            if folder.name.startswith("failure-postinstall-exec_1.0"):
                self.assertTrue(is_folder_ignored(folder))
                found = True
                break
        self.assertTrue(found)

    def test_cannot_uninstall_to_keep_dependencies(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_2.0"]))
        self.check_content(self.pm.list_installed_packages(), ["container-A_2.0", "container-C_1.0", "container-D_1.0"])

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["container-C_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["container-A_2.0", "container-C_1.0", "container-D_1.0"])

    def test_env(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["env-A_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["env-A_1.0", "env-B_1.0"])

        env = self.pm.build_packages_environment(PackageIdentifier.parse_list(["env-A_1.0"]))
        self.assertEqual(3, len(env_tolist(env)))
        self.assertEqual(
            [
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_ENV_A2", "Hello"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            env_tolist(env),
        )

        env = self.pm.build_packages_environment(PackageIdentifier.parse_list(["env-B_1.0", "env-A_1.0"]))
        self.assertEqual(5, len(env_tolist(env)))
        self.assertEqual(
            [
                ("LEAF_ENV_B", "BAR"),
                ("LEAF_PATH_B", "$PATH:{folder}/env-B_1.0".format(folder=self.install_folder)),
                ("LEAF_ENV_A", "FOO"),
                ("LEAF_ENV_A2", "Hello"),
                ("LEAF_PATH_A", "$PATH:{folder}/env-A_1.0:{folder}/env-B_1.0".format(folder=self.install_folder)),
            ],
            env_tolist(env),
        )
        self.assertFileContentEquals(self.install_folder / "env-A_1.0" / "dump.out", "dump.out")

    def test_silent_fail(self):
        with self.assertRaises(Exception):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-postinstall-exec_1.0"]))
        self.check_content(self.pm.list_installed_packages(), [])

        self.pm.install_packages(PackageIdentifier.parse_list(["failure-postinstall-exec-silent_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["failure-postinstall-exec-silent_1.0"])

    def test_cannot_install_badhash(self):
        with self.assertRaises(InvalidHashException):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-badhash_1.0"]))

    def test_outdated_leaf_version(self):
        with self.assertRaises(LeafOutOfDateException):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-minver_1.0"]))

    def test_outdated_cache_file(self):
        remote_cache_file = self.pm.cache_folder / "remotes" / "default.json"

        def get_mtime():
            return remote_cache_file.stat().st_mtime

        # Initial refresh
        self.pm.fetch_remotes(force_refresh=False)
        previous_mtime = get_mtime()

        # Second refresh, same day, file should not be updated
        time.sleep(1)
        self.pm.fetch_remotes(force_refresh=False)
        self.assertEqual(previous_mtime, get_mtime())
        os.remove(str(remote_cache_file))
        self.assertFalse(remote_cache_file.exists())

        # File has been deleted
        time.sleep(1)
        self.pm.fetch_remotes(force_refresh=False)
        self.assertNotEqual(previous_mtime, get_mtime())
        previous_mtime = get_mtime()

        # Initial refresh
        time.sleep(1)
        self.pm.fetch_remotes(force_refresh=False)
        self.assertEqual(previous_mtime, get_mtime())

        # New refresh, 23h ago, file should not be updated
        time.sleep(1)
        today = datetime.now()
        almostyesterday = today - timedelta(hours=23)
        os.utime(str(remote_cache_file), (int(almostyesterday.timestamp()), int(almostyesterday.timestamp())))
        self.assertNotEqual(previous_mtime, get_mtime())
        previous_mtime = get_mtime()
        self.pm.fetch_remotes(force_refresh=False)
        self.assertEqual(previous_mtime, get_mtime())

        # New refresh, 24h ago, file should be updated
        time.sleep(1)
        yesterday = today - timedelta(hours=24)
        os.utime(str(remote_cache_file), (int(yesterday.timestamp()), int(yesterday.timestamp())))
        self.assertNotEqual(previous_mtime, get_mtime())
        previous_mtime = get_mtime()
        self.pm.fetch_remotes(force_refresh=False)
        self.assertNotEqual(previous_mtime, get_mtime())

    def test_conditional_install(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["condition_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])

        self.pm.install_packages(PackageIdentifier.parse_list(["condition_1.0"]), env=Environment("test", {"FOO": "BAR"}))
        self.check_content(
            self.pm.list_installed_packages(),
            ["condition_1.0", "condition-A_1.0", "condition-B_1.0", "condition-C_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"],
        )

        self.pm.update_user_environment(set_map={"FOO2": "BAR2", "HELLO": "WoRld"})

        env = Environment.build(self.pm.build_builtin_environment(), self.pm.build_user_environment(), Environment("test", {"FOO": "BAR"}))
        self.pm.install_packages(PackageIdentifier.parse_list(["condition_1.0"]), env=env)
        self.check_content(
            self.pm.list_installed_packages(),
            [
                "condition_1.0",
                "condition-A_1.0",
                "condition-B_1.0",
                "condition-C_1.0",
                "condition-D_1.0",
                "condition-E_1.0",
                "condition-F_1.0",
                "condition-G_1.0",
                "condition-H_1.0",
            ],
        )

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["condition_1.0"]))
        self.check_content(self.pm.list_installed_packages(), [])

    def test_prereq_failure(self):
        with self.assertRaises(PrereqException):
            self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-prereq_0.1"]))

        self.check_content(self.pm.list_installed_packages(), ["prereq-A_0.1-fail"])
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_0.1-fail" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_0.1-fail" / "sync.log")))

        with self.assertRaises(PrereqException):
            self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-prereq_0.1"]))

        self.check_content(self.pm.list_installed_packages(), ["prereq-A_0.1-fail"])
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_0.1-fail" / "install.log")))
        self.assertEqual(2, len(get_lines(self.install_folder / "prereq-A_0.1-fail" / "sync.log")))

    def test_prereq(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-prereq_1.0"]))

        self.check_content(self.pm.list_installed_packages(), ["pkg-with-prereq_1.0", "prereq-A_1.0", "prereq-B_1.0"])

        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "sync.log")))

        self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-prereq_2.0"]))

        self.check_content(self.pm.list_installed_packages(), ["pkg-with-prereq_2.0", "pkg-with-prereq_1.0", "prereq-A_1.0", "prereq-B_1.0", "prereq-B_2.0"])

        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "install.log")))
        self.assertEqual(2, len(get_lines(self.install_folder / "prereq-A_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_2.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_2.0" / "sync.log")))

        self.pm.uninstall_packages(PackageIdentifier.parse_list(["pkg-with-prereq_2.0"]))
        self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-prereq_2.0"]))

        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "install.log")))
        self.assertEqual(3, len(get_lines(self.install_folder / "prereq-A_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_2.0" / "install.log")))
        self.assertEqual(2, len(get_lines(self.install_folder / "prereq-B_2.0" / "sync.log")))

    def test_deps_with_prereq(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-deps-with-prereq_1.0"]))

        self.check_content(self.pm.list_installed_packages(), ["pkg-with-deps-with-prereq_1.0", "pkg-with-prereq_1.0", "prereq-A_1.0", "prereq-B_1.0"])

        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "sync.log")))

    def test_depends_available(self):
        deps = DependencyUtils.install(PackageIdentifier.parse_list([]), self.pm.list_available_packages(), self.pm.list_installed_packages())
        self.__assert_deps(deps, [], AvailablePackage)

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages())
        self.__assert_deps(deps, ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0"], AvailablePackage)

    def test_depends_with_custom_env(self):
        env = Environment.build(self.pm.build_builtin_environment(), self.pm.build_user_environment(), Environment("Custom env", {}))
        deps = DependencyUtils.install(
            PackageIdentifier.parse_list(["condition_1.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages(), env=env
        )
        self.__assert_deps(deps, ["condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], AvailablePackage)

        self.pm.update_user_environment(set_map={"FOO": "HELLO"})
        env = Environment.build(self.pm.build_builtin_environment(), self.pm.build_user_environment(), Environment("Custom env", {}))
        deps = DependencyUtils.install(
            PackageIdentifier.parse_list(["condition_1.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages(), env=env
        )
        self.__assert_deps(deps, ["condition-A_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], AvailablePackage)

        self.pm.update_user_environment(set_map={"FOO": "HELLO"})
        env = Environment.build(self.pm.build_builtin_environment(), self.pm.build_user_environment(), Environment("Custom env", {"FOO": "BAR"}))
        deps = DependencyUtils.install(
            PackageIdentifier.parse_list(["condition_1.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages(), env=env
        )
        self.__assert_deps(deps, ["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], AvailablePackage)

    def test_depends_install(self):
        deps = DependencyUtils.install(PackageIdentifier.parse_list([]), self.pm.list_available_packages(), self.pm.list_installed_packages())
        self.__assert_deps(deps, [], AvailablePackage)

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages())
        self.__assert_deps(deps, ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0"], AvailablePackage)

        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_1.0"]))

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages())
        self.__assert_deps(deps, [], AvailablePackage)

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_2.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages())
        self.__assert_deps(deps, ["container-D_1.0", "container-A_2.0"], AvailablePackage)

    def test_depends_installed(self):
        deps = DependencyUtils.installed(PackageIdentifier.parse_list(["container-A_1.0"]), self.pm.list_installed_packages(), ignore_unknown=True)
        self.__assert_deps(deps, [], InstalledPackage)

        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_1.0"]))

        deps = DependencyUtils.installed(PackageIdentifier.parse_list(["container-A_1.0"]), self.pm.list_installed_packages())
        self.__assert_deps(deps, ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0"], InstalledPackage)

    def test_depends_uninstall(self):
        deps = DependencyUtils.uninstall(PackageIdentifier.parse_list([]), self.pm.list_installed_packages())
        self.__assert_deps(deps, [], InstalledPackage)

        self.pm.install_packages(PackageIdentifier.parse_list(["container-A_1.0"]))

        deps = DependencyUtils.uninstall(PackageIdentifier.parse_list(["container-A_1.0"]), self.pm.list_installed_packages())
        self.__assert_deps(deps, ["container-A_1.0", "container-C_1.0", "container-B_1.0", "container-E_1.0"], InstalledPackage)

    def test_depends_prereq(self):
        deps = DependencyUtils.prereq(
            PackageIdentifier.parse_list(["pkg-with-prereq_2.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages()
        )
        self.__assert_deps(deps, ["prereq-A_1.0", "prereq-B_2.0"], AvailablePackage)

        self.pm.install_packages(PackageIdentifier.parse_list(["pkg-with-prereq_1.0"]))
        deps = DependencyUtils.prereq(
            PackageIdentifier.parse_list(["pkg-with-prereq_2.0"]), self.pm.list_available_packages(), self.pm.list_installed_packages()
        )
        self.__assert_deps(deps, ["prereq-A_1.0", "prereq-B_2.0"], None)
        self.assertIsInstance(deps[0], InstalledPackage)
        self.assertIsInstance(deps[1], AvailablePackage)

    def __assert_deps(self, result, expected, itemtype):
        if itemtype is not None:
            for item in result:
                self.assertEqual(itemtype, type(item))
                self.assertTrue(isinstance(item, itemtype))
        deps = [str(mf.identifier) for mf in result]
        self.assertEqual(expected, deps)

    def test_sync(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["sync_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["sync_1.0"])
        self.check_installed_packages(["sync_1.0"])
        sync_file = self.install_folder / "sync_1.0" / "sync.log"

        self.assertFalse(sync_file.exists())

        self.pm.sync_packages(PackageIdentifier.parse_list(["sync_1.0"]))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE"], get_lines(sync_file))

        self.pm.sync_packages(PackageIdentifier.parse_list(["sync_1.0"]))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE"], get_lines(sync_file))

        self.pm.update_user_environment({"MYVAR2": "MYOTHERVALUE"})
        self.pm.sync_packages(PackageIdentifier.parse_list(["sync_1.0"]))
        self.assertTrue(sync_file.exists())
        self.assertEqual(["MYVALUE", "MYVALUE", "MYVALUE MYOTHERVALUE"], get_lines(sync_file))

    def test_resolve_latest(self):
        self.pm.install_packages(PackageIdentifier.parse_list(["version_1.0"]))
        self.check_content(self.pm.list_installed_packages(), ["version_1.0"])
        self.check_installed_packages(["version_1.0"])

        self.pm.install_packages(PackageIdentifier.parse_list(["version_1.1"]))
        self.check_content(self.pm.list_installed_packages(), ["version_1.0", "version_1.1"])
        self.check_installed_packages(["version_1.0", "version_1.1"])

        env = self.pm.build_packages_environment(PackageIdentifier.parse_list(["version_latest"]))
        self.assertEqual("1.1", env.find_value("TEST_VERSION"))

        self.pm.install_packages(PackageIdentifier.parse_list(["version_latest"]))
        self.check_content(self.pm.list_installed_packages(), ["version_1.0", "version_1.1", "version_2.0"])
        self.check_installed_packages(["version_1.0", "version_1.1", "version_2.0"])

        env = self.pm.build_packages_environment(PackageIdentifier.parse_list(["version_latest"]))
        self.assertEqual("2.0", env.find_value("TEST_VERSION"))

    def test_multiple_volatile_tags(self):
        def toggle_remote(name, enabled):
            remote = self.pm.list_remotes()[name]
            remote.enabled = enabled
            self.pm.update_remote(remote)

        pi = PackageIdentifier.parse("multitags_1.0")

        toggle_remote("other", False)
        self.assertEqual(["staticTag1", "staticTag2", "volatileTag1", "volatileTag2"], self.pm.list_available_packages()[pi].tags)

        toggle_remote("other", True)
        toggle_remote("default", False)
        self.assertEqual(["staticTag1", "staticTag2", "volatileTag3", "volatileTag4"], self.pm.list_available_packages()[pi].tags)

        toggle_remote("default", True)
        self.assertEqual(
            ["staticTag1", "staticTag2", "volatileTag1", "volatileTag2", "volatileTag3", "volatileTag4"], self.pm.list_available_packages()[pi].tags
        )

    def test_free_space_issue(self):
        with self.assertRaises(NotEnoughSpaceException):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-large-ap_1.0"]))
        with self.assertRaises(NotEnoughSpaceException):
            self.pm.install_packages(PackageIdentifier.parse_list(["failure-large-extracted_1.0"]))

    def test_tar_size(self):
        for filename, testfunc in (("compress-tar_1.0.leaf", self.assertGreater), ("compress-xz_1.0.leaf", self.assertLess)):
            file = self.repository_folder / filename
            self.assertTrue(file.exists())
            la = LeafArtifact(file)
            testfunc(file.stat().st_size, la.get_total_size())


def start_http_server(folder):
    print("Start http server for {folder} on port {port}".format(folder=folder, port=HTTP_PORT), file=sys.stderr)
    os.chdir(str(folder))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", HTTP_PORT.as_int()), SimpleHTTPRequestHandler)
    httpd.serve_forever()


@unittest.skipIf("http" in LEAF_UT_SKIP.value.lower(), "Test disabled")
class TestApiPackageManagerHttp(TestApiPackageManager):
    @classmethod
    def setUpClass(cls):
        TestApiPackageManager.setUpClass()
        print("Using http port {port}".format(port=HTTP_PORT), file=sys.stderr)
        TestApiPackageManagerHttp.process = Process(target=start_http_server, args=(LeafTestCaseWithRepo._TEST_FOLDER / "repository",))
        TestApiPackageManagerHttp.process.start()
        # Wait 10 seconds for the http server to start
        sleep(10)

    @classmethod
    def tearDownClass(cls):
        TestApiPackageManager.tearDownClass()
        print("Stopping http server ...", file=sys.stderr)
        TestApiPackageManagerHttp.process.terminate()
        TestApiPackageManagerHttp.process.join()
        print("Stopping http server ... done", file=sys.stderr)

    @property
    def remote_url1(self):
        return "http://localhost:{port}/index.json".format(port=HTTP_PORT)

    @property
    def remote_url2(self):
        return "http://localhost:{port}/index2.json".format(port=HTTP_PORT)
