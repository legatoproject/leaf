'''
@author: nico
'''

from collections import OrderedDict
import platform
import unittest

from leaf import __version__
from leaf.constants import LeafFiles, JsonConstants
from leaf.core.packagemanager import PackageManager, LoggerManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.format.logger import Verbosity
from leaf.format.renderer.environment import EnvironmentRenderer
from leaf.format.renderer.feature import FeatureListRenderer
from leaf.format.renderer.manifest import ManifestListRenderer
from leaf.format.renderer.profile import ProfileListRenderer
from leaf.format.renderer.remote import RemoteListRenderer
from leaf.format.renderer.workspace import WorkspaceRenderer
from leaf.model.environment import Environment
from leaf.model.package import Manifest, AvailablePackage, InstalledPackage,\
    PackageIdentifier, Feature
from leaf.model.remote import Remote
from leaf.utils import jsonLoadFile
from tests.testutils import LeafCliWrapper, LEAF_UT_SKIP, RESOURCE_FOLDER,\
    AbstractTestWithRepo


class AvailablePackageWithFakeSize(AvailablePackage):

    def __init__(self, manifestFile, remoteUrl):
        Manifest.__init__(self, jsonLoadFile(manifestFile))
        self.remoteUrl = remoteUrl
        self.sourceRemotes = []

    def getSize(self):
        return 0


class TestRendering_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)
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
        rend.extend(mfs)
        with self.assertStdout(
                templateOut="manifest.out",
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER,
                    "{RESOURCE_FOLDER}": RESOURCE_FOLDER}):
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

    def createWorkspace(self):
        AbstractTestWithRepo.setUp(self)
        pm = PackageManager(self.loggerManager.logger, nonInteractive=True)
        pm.setInstallFolder(self.getInstallFolder())
        pm.createRemote("default", self.getRemoteUrl(), insecure=True)
        ws = WorkspaceManager(
            WorkspaceManager.findRoot(
                customPath=self.getWorkspaceFolder(),
                checkEnv=False,
                checkParents=False),
            self.loggerManager.logger.getVerbosity(),
            True)
        ws.initializeWorkspace()

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
        rend = WorkspaceRenderer(self.createWorkspace()[0])
        with self.assertStdout(
                templateOut="workspace.out",
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER}):
            self.loggerManager.printRenderer(rend)

    def testProfile(self):
        rend = ProfileListRenderer(self.createWorkspace()[1])
        with self.assertStdout(
                templateOut="profile.out"):
            self.loggerManager.printRenderer(rend)

    def testFeature(self):
        rend = FeatureListRenderer()
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
        with self.assertStdout(
                templateOut="feature.out"):
            self.loggerManager.printRenderer(rend)


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


if __name__ == "__main__":
    unittest.main()
