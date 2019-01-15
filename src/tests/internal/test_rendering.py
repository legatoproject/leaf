'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os
import platform
import sys
import unittest

from leaf import __version__
from leaf.constants import EnvConstants, JsonConstants, LeafFiles
from leaf.core.packagemanager import LoggerManager, PackageManager
from leaf.format.logger import Verbosity
from leaf.format.renderer.environment import EnvironmentRenderer
from leaf.format.renderer.feature import FeatureListRenderer
from leaf.format.renderer.manifest import ManifestListRenderer
from leaf.format.renderer.profile import ProfileListRenderer
from leaf.format.renderer.remote import RemoteListRenderer
from leaf.model.environment import Environment
from leaf.model.package import AvailablePackage, Feature, InstalledPackage, Manifest
from leaf.model.remote import Remote
from leaf.model.workspace import Profile
from leaf.utils import jsonLoadFile

from leaf.core.error import LeafException
from leaf.format.renderer.status import StatusRenderer
from tests.testutils import LEAF_UT_SKIP, RESOURCE_FOLDER,\
    AbstractTestWithRepo, ROOT_FOLDER, AbstractTestWithChecker


class AvailablePackageWithFakeSize(AvailablePackage):

    def __init__(self, manifestFile, remoteUrl):
        Manifest.__init__(self, jsonLoadFile(manifestFile))
        self.remoteUrl = remoteUrl
        self.sourceRemotes = []

    def getSize(self):
        return 0


class TestRendering(AbstractTestWithChecker):

    def __init__(self, methodName):
        AbstractTestWithChecker.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.DEFAULT)

    def getRemoteUrl(self):
        return "http://fakeUrl"

    def loadManifest(self):
        out = []
        for packageFolder in RESOURCE_FOLDER.iterdir():
            if packageFolder.is_dir():
                manifestFile = packageFolder / LeafFiles.MANIFEST
                if manifestFile.is_file():
                    out.append(AvailablePackageWithFakeSize(
                        manifestFile, self.getRemoteUrl()))
                    ip = InstalledPackage(manifestFile)
                    ip.folder = "my/fake/folder"
                    out.append(ip)
        return sorted(out, key=lambda mf: str(type(mf)) + str(mf))

    def testManifest(self):
        mfs = self.loadManifest()
        rend = ManifestListRenderer()
        with self.assertStdout(
                templateOut="manifest.out",
                variables={"{RESOURCE_FOLDER}": RESOURCE_FOLDER}):
            self.loggerManager.printRenderer(rend)
            rend.extend(mfs)
            self.loggerManager.printRenderer(rend)

    def testRemote(self):
        rend = RemoteListRenderer()
        rend.append(Remote("MyRemote", {
            JsonConstants.CONFIG_REMOTE_ENABLED: True,
            JsonConstants.CONFIG_REMOTE_URL: "remote_url1"},
            content={
                JsonConstants.INFO: {
                    JsonConstants.REMOTE_NAME: "remote_name1",
                    JsonConstants.REMOTE_DESCRIPTION: "remote_desc1",
                    JsonConstants.REMOTE_DATE: "remote_date1"}}))
        rend.append(Remote("AnotherRemoteWithLessInfo", {
            JsonConstants.CONFIG_REMOTE_ENABLED: True,
            JsonConstants.CONFIG_REMOTE_URL: "remote_url1"}))
        rend.append(Remote("DisabledRemote", {
            JsonConstants.CONFIG_REMOTE_ENABLED: False,
            JsonConstants.CONFIG_REMOTE_URL: "remote_url3"},
            content={
                JsonConstants.INFO: {
                    JsonConstants.REMOTE_NAME: "remote_name3",
                    JsonConstants.REMOTE_DESCRIPTION: "remote_desc3",
                    JsonConstants.REMOTE_DATE: "remote_date3"}}))
        with self.assertStdout(
                templateOut="remotes.out"):
            self.loggerManager.printRenderer(RemoteListRenderer())
            self.loggerManager.printRenderer(rend)

    def testEnvironment(self):
        pm = PackageManager(self.loggerManager.logger)
        env = Environment.build(pm.getBuiltinEnvironment(),
                                pm.getUserEnvironment(),
                                Environment("test", {"FOO": "BAR"}))
        rend = EnvironmentRenderer(env)
        with self.assertStdout(
                templateOut="env.out",
                variables={"{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER,
                           "{LEAF_VERSION}": __version__,
                           "{PLATFORM_SYSTEM}": platform.system(),
                           "{PLATFORM_MACHINE}": platform.machine(),
                           "{PLATFORM_RELEASE}": platform.release()}):
            self.loggerManager.printRenderer(rend)

    def testStatus(self):
        profile1 = Profile("profile1", "fake/folder", {
            JsonConstants.WS_PROFILE_ENV: {
                "Foo1": "Bar1",
                "Foo2": "Bar2",
                "Foo3": "Bar3",
            }})
        profile1.isCurrentProfile = True
        profile2 = Profile("profile2", "fake/folder", {})
        profile2.isCurrentProfile = True
        profile3 = Profile("profile3", "fake/folder", {})
        profile3.isCurrentProfile = True
        p1 = Manifest({
            JsonConstants.INFO: {
                JsonConstants.INFO_NAME: "container-A",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "Fake description for container A"}})
        p2 = Manifest({
            JsonConstants.INFO: {
                JsonConstants.INFO_NAME: "container-B",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "Fake description for container B"}})
        p3 = Manifest({
            JsonConstants.INFO: {
                JsonConstants.INFO_NAME: "container-C",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "Fake description for container C"}})

        with self.assertStdout(
                templateOut="status.out"):
            print("####### Test with 2 other profiles, 2 incl, 1 deps #######")
            self.loggerManager.printRenderer(StatusRenderer(
                workspaceRootFolder="fake/root/folder",
                currentProfile=profile1,
                sync=True,
                includedPackagesMap={
                    p1.getIdentifier(): p1, p2.getIdentifier(): p2},
                dependenciesMap={
                    p3.getIdentifier(): p3},
                otherProfiles=[profile2, profile3]))
            print("\n\n\n####### Test with 1 other profile, 0 incl, 2 deps #######")
            self.loggerManager.printRenderer(StatusRenderer(
                workspaceRootFolder="fake/root/folder",
                currentProfile=profile1,
                sync=True,
                includedPackagesMap={},
                dependenciesMap={
                    p3.getIdentifier(): p3, p2.getIdentifier(): p2},
                otherProfiles=[profile2]))
            print("\n\n\n####### Test with 1 other profile, 1 incl, 0 deps #######")
            self.loggerManager.printRenderer(StatusRenderer(
                workspaceRootFolder="fake/root/folder",
                currentProfile=profile1,
                sync=False,
                includedPackagesMap={p3.getIdentifier(): p3},
                dependenciesMap={},
                otherProfiles=[profile2]))
            print(
                "\n\n\n####### Test with no other profiles, no included nor deps nor envvars #######")
            self.loggerManager.printRenderer(StatusRenderer(
                workspaceRootFolder="fake/root/folder",
                currentProfile=profile2,
                sync=False,
                includedPackagesMap={},
                dependenciesMap={},
                otherProfiles=[]))

    def testProfile(self):
        pack1 = Manifest({
            JsonConstants.INFO: {
                JsonConstants.INFO_NAME: "container-A",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "Fake description for container A"}})
        pack2 = Manifest({
            JsonConstants.INFO: {
                JsonConstants.INFO_NAME: "container-B",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "Fake description for container B"}})
        pack3 = Manifest({
            JsonConstants.INFO: {
                JsonConstants.INFO_NAME: "container-C",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "Fake description for container C"}})
        profile1 = Profile("profile1", "fake/folder", {
            JsonConstants.WS_PROFILE_ENV: {
                "Foo1": "Bar1",
                "Foo2": "Bar2",
                "Foo3": "Bar3",
            }})
        profile2 = Profile("profile2", "fake/folder", {})
        profile2.isCurrentProfile = True
        profile3 = Profile("profile3", "fake/folder", {
            JsonConstants.WS_PROFILE_ENV: {
                "Foo2": "Bar2",
                "Foo3": "Bar3",
            }})
        profile4 = Profile("profile4", "fake/folder", {})
        profilesInfoMap = {
            profile2: {
                "sync": False,
                "includedPackagesMap": {pack2.getIdentifier(): pack2},
                "dependenciesMap": {}},
            profile3: {
                "sync": True,
                "includedPackagesMap": {},
                "dependenciesMap": {pack2.getIdentifier(): pack2}},
            profile1: {
                "sync": True,
                "includedPackagesMap": {pack1.getIdentifier(): pack1},
                "dependenciesMap": {pack2.getIdentifier(): pack2, pack3.getIdentifier(): pack3, }},
            profile4: {
                "sync": False,
                "includedPackagesMap": {},
                "dependenciesMap": {}},
        }
        with self.assertStdout(templateOut="profile.out"):
            print("####### Test with no profile #######")
            self.loggerManager.printRenderer(ProfileListRenderer(
                workspaceRootFolder="fake/root/folder",
                profilesInfoMap={}))
            print("\n\n\n####### Test with various profiles #######")
            self.loggerManager.printRenderer(ProfileListRenderer(
                workspaceRootFolder="fake/root/folder",
                profilesInfoMap=profilesInfoMap))

    def testFeature(self):
        rend = FeatureListRenderer()
        with self.assertStdout(
                templateOut="feature.out"):
            self.loggerManager.printRenderer(rend)
            rend.append(Feature("id1", {
                JsonConstants.INFO_FEATURE_KEY: "KEY1",
                JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                JsonConstants.INFO_FEATURE_DESCRIPTION: "message1"
            }))
            rend.append(Feature("id2", {
                JsonConstants.INFO_FEATURE_KEY: "KEY2",
                JsonConstants.INFO_FEATURE_VALUES: {"enum2": "value2", "enum3": "value3"},
                JsonConstants.INFO_FEATURE_DESCRIPTION: "message2"
            }))
            self.loggerManager.printRenderer(rend)

    def _createException(self):
        ex = LeafException("Random message for this exception")
        ex.hints.append("this is a first hint with a 'command'")
        ex.hints.append(
            "another one with 'a first command' and 'a second one'")
        ex.cause = Exception("This is a fake cause exception")
        return ex

    def testHints(self):
        with self.assertStdout(
                templateOut="hints.out"):
            self.loggerManager.printHints(
                "This is a hints", "This is another hint with a 'fake command'")

    def testError(self):
        with self.assertStdout(
                templateOut=[],
                templateErr="error.err"):
            self.loggerManager.printException(self._createException())

    def _printError(self):
        try:
            1 / 0  # Ooops !
        except Exception as cause:
            ex = self._createException()
            ex.cause = cause
            print("---- Rendered error ----", file=sys.stderr)
            self.loggerManager.printException(ex)
            print("---- Logger error ----", file=sys.stderr)
            self.loggerManager.logger.printError(ex)

    def testTrace(self):
        with self.assertStdout(
                templateOut=[],
                templateErr="trace.err",
                variables={
                    "{ROOT_FOLDER}": ROOT_FOLDER}):
            print("--------- Production mode ---------", file=sys.stderr)
            self._printError()
            os.environ[EnvConstants.DEBUG_MODE] = "1"
            print("--------- Debug mode ---------", file=sys.stderr)
            self._printError()
            del os.environ[EnvConstants.DEBUG_MODE]


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestRenderingVerbose(TestRendering):
    def __init__(self, methodName):
        TestRendering.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.VERBOSE)


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestRenderingQuiet(TestRendering):
    def __init__(self, methodName):
        TestRendering.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.QUIET)
