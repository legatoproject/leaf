"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import sys
from pathlib import Path

from leaf.api import LoggerManager, PackageManager
from leaf.core.constants import JsonConstants, LeafFiles, LeafSettings
from leaf.core.error import LeafException
from leaf.core.jsonutils import jloadfile, jloads
from leaf.model.environment import Environment
from leaf.model.package import AvailablePackage, Feature, InstalledPackage, Manifest
from leaf.model.remote import Remote
from leaf.model.workspace import Profile
from leaf.rendering.ansi import ANSI
from leaf.rendering.renderer.environment import EnvironmentRenderer
from leaf.rendering.renderer.feature import FeatureListRenderer
from leaf.rendering.renderer.manifest import ManifestListRenderer
from leaf.rendering.renderer.profile import ProfileListRenderer
from leaf.rendering.renderer.remote import RemoteListRenderer
from leaf.rendering.renderer.status import StatusRenderer
from tests.testutils import RESOURCE_FOLDER, LeafTestCase

FAKE_URL = "http://fakeUrl"
FAKE_ENV_123 = """
{
    "env": {
        "Foo1": "Bar1",
        "Foo2": "Bar2",
        "Foo3": "Bar3"
    }
}
"""
FAKE_ENV_23 = """
{
    "env": {
        "Foo2": "Bar2",
        "Foo3": "Bar3"
    }
}
"""


class AvailablePackage2(AvailablePackage):
    @property
    def size(self):
        return 0


class InstalledPackage2(InstalledPackage):
    @property
    def folder(self):
        return Path("/fake/folder")


class TestRendering(LeafTestCase):
    def __init__(self, *args, **kwargs):
        LeafTestCase.__init__(self, *args, **kwargs)
        self.loggerManager = LoggerManager()

    def __load_manifest(self):
        out = []
        for folder in RESOURCE_FOLDER.iterdir():
            if folder.is_dir():
                mffile = folder / LeafFiles.MANIFEST
                if mffile.is_file():
                    out.append(AvailablePackage2(jloadfile(mffile), FAKE_URL))
                    out.append(InstalledPackage2(mffile))
        return sorted(out, key=lambda mf: str(type(mf)) + str(mf))

    def test_manifest(self):
        mflist = self.__load_manifest()
        rend = ManifestListRenderer()
        with self.assertStdout(template_out="manifest.out", variables={"{RESOURCE_FOLDER}": RESOURCE_FOLDER}):
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
        profile1 = Profile("profile1", "fake/folder", jloads(FAKE_ENV_123))
        profile1.is_current = True
        profile2 = Profile("profile2", "fake/folder", {})
        profile2.is_current = True
        profile3 = Profile("profile3", "fake/folder", {})
        profile3.is_current = True
        p1 = Manifest(
            {
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "container-A",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "Fake description for container A",
                }
            }
        )
        p2 = Manifest(
            {
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "container-B",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "Fake description for container B",
                }
            }
        )
        p3 = Manifest(
            {
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "container-C",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "Fake description for container C",
                }
            }
        )

        with self.assertStdout(template_out="status.out"):
            print("####### Test with 2 other profiles, 2 incl, 1 deps #######")
            self.loggerManager.print_renderer(
                StatusRenderer(
                    ws_root_folder="fake/root/folder",
                    current_profile=profile1,
                    sync=True,
                    included_packages_map={p1.identifier: p1, p2.identifier: p2},
                    dependencies_map={p3.identifier: p3},
                    other_profiles=[profile2, profile3],
                )
            )
            print("\n\n\n####### Test with 1 other profile, 0 incl, 2 deps #######")
            self.loggerManager.print_renderer(
                StatusRenderer(
                    ws_root_folder="fake/root/folder",
                    current_profile=profile1,
                    sync=True,
                    included_packages_map={},
                    dependencies_map={p3.identifier: p3, p2.identifier: p2},
                    other_profiles=[profile2],
                )
            )
            print("\n\n\n####### Test with 1 other profile, 1 incl, 0 deps #######")
            self.loggerManager.print_renderer(
                StatusRenderer(
                    ws_root_folder="fake/root/folder",
                    current_profile=profile1,
                    sync=False,
                    included_packages_map={p3.identifier: p3},
                    dependencies_map={},
                    other_profiles=[profile2],
                )
            )
            print("\n\n\n####### Test with no other profiles, no included nor deps nor envvars #######")
            self.loggerManager.print_renderer(
                StatusRenderer(
                    ws_root_folder="fake/root/folder", current_profile=profile2, sync=False, included_packages_map={}, dependencies_map={}, other_profiles=[]
                )
            )

    def test_profile(self):
        pack1 = Manifest(
            {
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "container-A",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "Fake description for container A",
                }
            }
        )
        pack2 = Manifest(
            {
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "container-B",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "Fake description for container B",
                }
            }
        )
        pack3 = Manifest(
            {
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "container-C",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "Fake description for container C",
                }
            }
        )
        profile1 = Profile("profile1", "fake/folder", jloads(FAKE_ENV_123))
        profile2 = Profile("profile2", "fake/folder", {})
        profile2.is_current = True
        profile3 = Profile("profile3", "fake/folder", jloads(FAKE_ENV_23))
        profile4 = Profile("profile4", "fake/folder", {})
        profiles_infomap = {
            profile2: {"sync": False, "included_packages_map": {pack2.identifier: pack2}, "dependencies_map": {}},
            profile3: {"sync": True, "included_packages_map": {}, "dependencies_map": {pack2.identifier: pack2}},
            profile1: {
                "sync": True,
                "included_packages_map": {pack1.identifier: pack1},
                "dependencies_map": {pack2.identifier: pack2, pack3.identifier: pack3},
            },
            profile4: {"sync": False, "included_packages_map": {}, "dependencies_map": {}},
        }
        with self.assertStdout(template_out="profile.out"):
            print("####### Test with no profile #######")
            self.loggerManager.print_renderer(ProfileListRenderer(Path("fake/root/folder"), {}))
            print("\n\n\n####### Test with various profiles #######")
            self.loggerManager.print_renderer(ProfileListRenderer(Path("fake/root/folder"), profiles_infomap))

    def test_feature(self):
        rend = FeatureListRenderer()
        with self.assertStdout(template_out="feature.out"):
            self.loggerManager.print_renderer(rend)
            rend.append(
                Feature(
                    "id1",
                    {
                        JsonConstants.INFO_FEATURE_KEY: "KEY1",
                        JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                        JsonConstants.INFO_FEATURE_DESCRIPTION: "message1",
                    },
                )
            )
            rend.append(
                Feature(
                    "id2",
                    {
                        JsonConstants.INFO_FEATURE_KEY: "KEY2",
                        JsonConstants.INFO_FEATURE_VALUES: {"enum2": "value2", "enum3": "value3"},
                        JsonConstants.INFO_FEATURE_DESCRIPTION: "message2",
                    },
                )
            )
            self.loggerManager.print_renderer(rend)

    def __create_exception(self, cause=None):
        if cause is None:
            cause = Exception("This is a fake cause exception")
        return LeafException(
            "Random message for this exception",
            cause=cause,
            hints=["this is a first hint with a 'command'", "another one with 'a first command' and 'a second one'"],
        )

    def test_hints(self):
        with self.assertStdout(template_out="hints.out"):
            self.loggerManager.print_hints("This is a hints", "This is another hint with a 'fake command'")

    def test_error(self):
        with self.assertStdout(template_out=[], template_err="error.err"):
            self.loggerManager.print_exception(self.__create_exception())

    def __print_error(self):
        try:
            1 / 0  # Ooops !
        except Exception as cause:
            ex = self.__create_exception(cause)
            print("---- Rendered error ----", file=sys.stderr)
            self.loggerManager.print_exception(ex)
            print("---- Logger error ----", file=sys.stderr)
            self.loggerManager.logger.print_error(ex)

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
