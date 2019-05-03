"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import sys
from pathlib import Path

from leaf.api import LoggerManager, PackageManager
from leaf.core.constants import JsonConstants, LeafFiles, LeafSettings
from leaf.core.error import LeafException
from leaf.core.jsonutils import jloadfile, jloads
from leaf.core.settings import RegexValidator
from leaf.model.base import Scope
from leaf.model.environment import Environment
from leaf.model.package import AvailablePackage, InstalledPackage, Manifest, ScopeSetting
from leaf.model.remote import Remote
from leaf.model.workspace import Profile
from leaf.rendering.ansi import ANSI
from leaf.rendering.renderer.environment import EnvironmentRenderer
from leaf.rendering.renderer.manifest import ManifestListRenderer
from leaf.rendering.renderer.profile import ProfileListRenderer
from leaf.rendering.renderer.remote import RemoteListRenderer
from leaf.rendering.renderer.settings import SettingsListRenderer
from leaf.rendering.renderer.status import StatusRenderer
from tests.testutils import TEST_REMOTE_PACKAGE_SOURCE, LeafTestCase


class AvailablePackage2(AvailablePackage):
    @property
    def size(self):
        return 0


class InstalledPackage2(InstalledPackage):
    @property
    def folder(self):
        return Path("/fake/folder")


class TestRendering(LeafTestCase):

    PKG1 = Manifest(jloads('{"info": {"name": "container-A","version": "1.0","description": "Fake description for container A"}}'))
    PKG2 = Manifest(jloads('{"info": {"name": "container-B","version": "1.0","description": "Fake description for container B"}}'))
    PKG3 = Manifest(jloads('{"info": {"name": "container-C","version": "1.0","description": "Fake description for container C"}}'))

    def __init__(self, *args, **kwargs):
        LeafTestCase.__init__(self, *args, **kwargs)
        self.loggerManager = LoggerManager()

    def __print_error(self):
        try:
            1 / 0  # Ooops !
        except Exception as cause:
            ex = self.__create_exception(cause)
            print("---- Rendered error ----", file=sys.stderr)
            self.loggerManager.print_exception(ex)
            print("---- Logger error ----", file=sys.stderr)
            self.loggerManager.logger.print_error(ex)

    def __create_exception(self, cause=None):
        if cause is None:
            cause = Exception("This is a fake cause exception")
        return LeafException(
            "Random message for this exception",
            cause=cause,
            hints=["this is a first hint with a 'command'", "another one with 'a first command' and 'a second one'"],
        )

    def __load_manifest(self):
        out = []
        for folder in TEST_REMOTE_PACKAGE_SOURCE.iterdir():
            if folder.is_dir():
                mffile = folder / LeafFiles.MANIFEST
                if mffile.is_file():
                    out.append(AvailablePackage2(jloadfile(mffile), "http://fakeUrl"))
                    out.append(InstalledPackage2(mffile))
        return sorted(out, key=lambda mf: str(type(mf)) + str(mf))

    def test_manifest(self):
        mflist = self.__load_manifest()
        rend = ManifestListRenderer()
        with self.assertStdout(template_out="manifest.out"):
            self.loggerManager.print_renderer(rend)
            rend.extend(mflist)
            self.loggerManager.print_renderer(rend)

    def test_remote(self):
        rend = RemoteListRenderer()
        rend.append(
            Remote(
                "MyRemote",
                {JsonConstants.CONFIG_REMOTE_ENABLED: True, JsonConstants.CONFIG_REMOTE_URL: "remote_url1"},
                content={
                    JsonConstants.INFO: {
                        JsonConstants.REMOTE_NAME: "remote_name1",
                        JsonConstants.REMOTE_DESCRIPTION: "remote_desc1",
                        JsonConstants.REMOTE_DATE: "remote_date1",
                    }
                },
            )
        )
        rend.append(Remote("AnotherRemoteWithLessInfo", {JsonConstants.CONFIG_REMOTE_ENABLED: True, JsonConstants.CONFIG_REMOTE_URL: "remote_url1"}))
        rend.append(
            Remote(
                "DisabledRemote",
                {JsonConstants.CONFIG_REMOTE_ENABLED: False, JsonConstants.CONFIG_REMOTE_URL: "remote_url3"},
                content={
                    JsonConstants.INFO: {
                        JsonConstants.REMOTE_NAME: "remote_name3",
                        JsonConstants.REMOTE_DESCRIPTION: "remote_desc3",
                        JsonConstants.REMOTE_DATE: "remote_date3",
                    }
                },
            )
        )
        with self.assertStdout(template_out="remotes.out"):
            self.loggerManager.print_renderer(RemoteListRenderer())
            self.loggerManager.print_renderer(rend)

    def test_environment(self):
        pm = PackageManager()
        env = Environment.build(pm.build_builtin_environment(), pm.build_user_environment(), Environment("test", {"FOO": "BAR"}))
        rend = EnvironmentRenderer(env)
        with self.assertStdout(template_out="env.out"):
            self.loggerManager.print_renderer(rend)

    def test_status(self):
        profile1 = Profile(
            "profile1",
            "fake/folder",
            jloads('{"env": {"Foo1": "Bar1", "Foo2": "Bar2", "Foo3": "Bar3"}, "packages": {"container-A": "1.0", "container-B": "1.0"}}'),
        )
        profile2 = Profile("profile2", "fake/folder", {})
        profile3 = Profile("profile3", "fake/folder", jloads('{"packages": {"container-C": "1.0"}}'))

        with self.assertStdout(template_out="status.out"):
            print("####### Test with 2 other profiles, 2 incl, 1 deps #######")
            profile1.is_current = True
            profile2.is_current = False
            profile3.is_current = False
            renderer = StatusRenderer(Path("fake/root/folder"), Environment("test", {"WS_KEY": "VALUE"}))
            renderer.append_profile(profile1, True, [TestRendering.PKG1, TestRendering.PKG2, TestRendering.PKG3])
            renderer.append_profile(profile2, False, [])
            renderer.append_profile(profile3, False, [])
            self.loggerManager.print_renderer(renderer)

            print("\n\n\n####### Test with 1 other profile, 0 incl, 0 deps #######")
            profile1.is_current = False
            profile2.is_current = True
            profile3.is_current = False
            renderer = StatusRenderer(Path("fake/root/folder"), Environment("test", {"WS_KEY": "VALUE"}))
            renderer.append_profile(profile1, True, [TestRendering.PKG1, TestRendering.PKG2, TestRendering.PKG3])
            renderer.append_profile(profile2, False, [])
            self.loggerManager.print_renderer(renderer)

            print("\n\n\n####### Test with 1 other profile, 1 incl (not fetched), 0 deps #######")
            profile1.is_current = False
            profile2.is_current = False
            profile3.is_current = True
            renderer = StatusRenderer(Path("fake/root/folder"), Environment("test", {"WS_KEY": "VALUE"}))
            renderer.append_profile(profile2, False, [])
            renderer.append_profile(profile3, False, [])
            self.loggerManager.print_renderer(renderer)

            print("\n\n\n####### Test with no other profiles, no included nor deps nor envvars #######")
            profile1.is_current = False
            profile2.is_current = True
            profile3.is_current = False
            renderer = StatusRenderer(Path("fake/root/folder"), Environment("test", {"WS_KEY": "VALUE"}))
            renderer.append_profile(profile2, False, [])
            self.loggerManager.print_renderer(renderer)

    def test_profile(self):

        profile1 = Profile("profile1", "fake/folder", jloads('{"env": {"Foo1": "Bar1", "Foo2": "Bar2", "Foo3": "Bar3"}, "packages": {"container-A": "1.0"}}'))
        profile2 = Profile("profile2", "fake/folder", jloads('{"packages": {"container-B": "1.0"}}'))
        profile2.is_current = True
        profile3 = Profile("profile3", "fake/folder", jloads('{"env": {"Foo2": "Bar2", "Foo3": "Bar3"}}'))
        profile4 = Profile("profile4", "fake/folder", {})
        with self.assertStdout(template_out="profile.out"):
            print("####### Test with no profile #######")
            renderer = ProfileListRenderer(Path("fake/root/folder"), Environment("test", {"WS_KEY": "VALUE"}))
            self.loggerManager.print_renderer(renderer)
            print("\n\n\n####### Test with various profiles #######")
            renderer.append_profile(profile1, True, [TestRendering.PKG1, TestRendering.PKG2, TestRendering.PKG3])
            renderer.append_profile(profile2, False, [TestRendering.PKG2])
            renderer.append_profile(profile3, True, [TestRendering.PKG2])
            renderer.append_profile(profile4, False, [])
            self.loggerManager.print_renderer(renderer)

    def test_settings(self):
        for filter_unset in (True, False):
            with self.assertStdout(template_out="filter{filter}.out".format(filter=filter_unset)):
                rend = SettingsListRenderer(Path("/fake/folder"), {"foo.id1": "Hello world"}, filter_unset=filter_unset)
                self.loggerManager.print_renderer(rend)

                rend.append(ScopeSetting("foo.id1", "KEY", None, [Scope.USER]))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER]))
                rend.append(ScopeSetting("foo.id2", "KEY", "some description", [Scope.USER]))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER, Scope.WORKSPACE, Scope.PROFILE]))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER, Scope.WORKSPACE]))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER, Scope.PROFILE]))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.WORKSPACE, Scope.PROFILE]))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER], default="Hello"))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER], validator=RegexValidator(".*")))
                rend.append(ScopeSetting("foo.id1", "KEY", "some description", [Scope.USER], validator=RegexValidator("(HELLO|WORLD)")))
                self.loggerManager.print_renderer(rend)

    def test_hints(self):
        with self.assertStdout(template_out="hints.out"):
            self.loggerManager.print_hints("This is a hints", "This is another hint with a 'fake command'")

    def test_error(self):
        with self.assertStdout(template_out=[], template_err="error.err"):
            self.loggerManager.print_exception(self.__create_exception())

    def test_trace(self):
        with self.assertStdout(template_out=[], template_err="trace.err"):
            LeafSettings.DEBUG_MODE.value = None
            print("--------- Production mode ---------", file=sys.stderr)
            self.__print_error()

            LeafSettings.DEBUG_MODE.value = 1
            print("--------- Debug mode ---------", file=sys.stderr)
            self.__print_error()
            LeafSettings.DEBUG_MODE.value = None


class TestRenderingVerbose(TestRendering):
    def __init__(self, *args, **kwargs):
        TestRendering.__init__(self, *args, verbosity="verbose", **kwargs)


class TestRenderingQuiet(TestRendering):
    def __init__(self, *args, **kwargs):
        TestRendering.__init__(self, *args, verbosity="quiet", **kwargs)


class TestRenderingAnsi(TestRendering):
    @classmethod
    def setUpClass(cls):
        ANSI.force = True
        TestRendering.setUpClass()

    @classmethod
    def tearDownClass(cls):
        TestRendering.tearDownClass()
        ANSI.force = False


class TestRenderingAnsiVerbose(TestRenderingAnsi):
    def __init__(self, *args, **kwargs):
        TestRenderingAnsi.__init__(self, *args, verbosity="verbose", **kwargs)


class TestRenderingAnsiQuiet(TestRenderingAnsi):
    def __init__(self, *args, **kwargs):
        TestRenderingAnsi.__init__(self, *args, verbosity="quiet", **kwargs)
