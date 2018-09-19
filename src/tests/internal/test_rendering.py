'''
@author: nico
'''

import os
import platform
import sys
import unittest
from collections import OrderedDict

from leaf import __version__
from leaf.constants import EnvConstants, JsonConstants, LeafFiles
from leaf.core.error import LeafException
from leaf.core.packagemanager import LoggerManager, PackageManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.format.logger import Verbosity
from leaf.format.renderer.environment import EnvironmentRenderer
from leaf.format.renderer.feature import FeatureListRenderer
from leaf.format.renderer.manifest import ManifestListRenderer
from leaf.format.renderer.profile import ProfileListRenderer
from leaf.format.renderer.remote import RemoteListRenderer
from leaf.format.renderer.workspace import WorkspaceRenderer
from leaf.model.environment import Environment
from leaf.model.package import AvailablePackage, Feature, InstalledPackage, \
    Manifest, PackageIdentifier
from leaf.model.remote import Remote
from leaf.utils import jsonLoadFile
from tests.testutils import AbstractTestWithRepo, LEAF_UT_SKIP, \
    RESOURCE_FOLDER, ROOT_FOLDER


class AvailablePackageWithFakeSize(AvailablePackage):

    def __init__(self, manifestFile, remoteUrl):
        Manifest.__init__(self, jsonLoadFile(manifestFile))
        self.remoteUrl = remoteUrl
        self.sourceRemotes = []

    def getSize(self):
        return 0


class TestRendering_Default(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.DEFAULT, True)

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
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER,
                    "{RESOURCE_FOLDER}": RESOURCE_FOLDER}):
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
        pm = PackageManager(self.loggerManager.logger, nonInteractive=True)
        env = Environment.build(pm.getLeafEnvironment(),
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

    def createEmptyWs(self):
        ws = WorkspaceManager(WorkspaceManager.findRoot(
            customPath=self.getWorkspaceFolder(),
            checkEnv=False,
            checkParents=False),
            self.loggerManager.logger.getVerbosity(),
            True)
        ws.initializeWorkspace()
        return ws

    def createWorkspace(self):
        AbstractTestWithRepo.setUp(self)
        pm = PackageManager(self.loggerManager.logger, nonInteractive=True)
        pm.setInstallFolder(self.getInstallFolder())
        pm.createRemote("default", self.getRemoteUrl(), insecure=True)
        ws = self.createEmptyWs()

        pfs = []
        profile = ws.createProfile("foo")
        profile.addPackages(
            PackageIdentifier.fromStringList(["container-A_1.0"]))
        profile.updateEnv(OrderedDict([("FOO", "BAR"),
                                       ("FOO2", "BAR2")]))
        profile = ws.updateProfile(profile)
        pfs.append(profile)

        profile = ws.createProfile("bar")
        profile.addPackages(
            PackageIdentifier.fromStringList(["container-B_1.0"]))
        profile = ws.updateProfile(profile)
        pfs.append(profile)

        ws.readConfiguration()
        return ws, pfs

    def testWorkspace(self):
        with self.assertStdout(
                templateOut="workspace.out",
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER}):
            self.loggerManager.printRenderer(
                WorkspaceRenderer(self.createEmptyWs()))
            self.loggerManager.printRenderer(
                WorkspaceRenderer(self.createWorkspace()[0]))

    def testProfile(self):
        with self.assertStdout(
                templateOut="profile.out"):
            self.loggerManager.printRenderer(ProfileListRenderer())
            self.loggerManager.printRenderer(
                ProfileListRenderer(self.createWorkspace()[1]))

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
                "This is a hints", "This is another hints with a 'fake command'")

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
class TestRendering_Verbose(TestRendering_Default):
    def __init__(self, methodName):
        TestRendering_Default.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.VERBOSE, True)


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestRendering_Quiet(TestRendering_Default):
    def __init__(self, methodName):
        TestRendering_Default.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.QUIET, True)
