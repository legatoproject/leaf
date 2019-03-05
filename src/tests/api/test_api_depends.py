"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from collections import OrderedDict

from leaf.core.constants import LeafFiles
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import IDENTIFIER_GETTER, Manifest, PackageIdentifier
from tests.testutils import RESOURCE_FOLDER, LeafTestCase


def deps2strlist(deps):
    return list(map(str, map(IDENTIFIER_GETTER, deps)))


class TestApiDepends(LeafTestCase):

    MANIFEST_MAP = {}

    @classmethod
    def setUpClass(cls):
        for f in RESOURCE_FOLDER.iterdir():
            mffile = f / LeafFiles.MANIFEST
            if mffile.exists():
                try:
                    mf = Manifest.parse(mffile)
                    TestApiDepends.MANIFEST_MAP[mf.identifier] = mf
                except Exception:
                    pass
        print("Found", len(TestApiDepends.MANIFEST_MAP), LeafFiles.MANIFEST)

    def test_install(self):
        apmpa = TestApiDepends.MANIFEST_MAP
        ipmap = {}
        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), apmpa, ipmap, env=Environment())
        self.assertEqual(["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"], deps2strlist(deps))

        pi = PackageIdentifier.parse("container-E_1.0")
        ipmap[pi] = TestApiDepends.MANIFEST_MAP.get(pi)

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), apmpa, ipmap, env=Environment())
        self.assertEqual(["container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"], deps2strlist(deps))

    def test_uninstall(self):

        apmap = TestApiDepends.MANIFEST_MAP
        ipmap = OrderedDict()

        for ap in DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), apmap, ipmap):
            ipmap[ap.identifier] = ap

        self.assertEqual(
            ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"], deps2strlist(ipmap.values())
        )

        deps = DependencyUtils.uninstall(PackageIdentifier.parse_list(["container-A_1.0"]), ipmap)

        self.assertEqual(["container-A_1.0", "container-B_1.0", "container-E_1.0"], deps2strlist(deps))

    def test_conditional_install(self):
        apmap = TestApiDepends.MANIFEST_MAP
        ipmap = {}

        def _getdeps(env):
            return DependencyUtils.install(PackageIdentifier.parse_list(["condition_1.0"]), apmap, ipmap, env=env)

        env = Environment()
        deps = _getdeps(env)
        self.assertEqual(["condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2", "HELLO": "wOrlD"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-E_1.0", "condition-G_1.0", "condition_1.0"], deps2strlist(deps))

        pi = PackageIdentifier.parse("condition-C_1.0")
        ipmap[pi] = TestApiDepends.MANIFEST_MAP.get(pi)

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2", "HELLO": "wOrlD"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-E_1.0", "condition-G_1.0", "condition_1.0"], deps2strlist(deps))

    def test_conditional_tree(self):
        apmap = TestApiDepends.MANIFEST_MAP

        def _getdeps(env):
            return DependencyUtils.install(PackageIdentifier.parse_list(["condition_1.0"]), apmap, {}, env=env)

        env = Environment()
        deps = _getdeps(env)
        self.assertEqual(["condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2", "HELLO": "wOrlD"})
        deps = _getdeps(env)
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-E_1.0", "condition-G_1.0", "condition_1.0"], deps2strlist(deps))

        deps = _getdeps(None)
        self.assertEqual(
            [
                "condition-A_1.0",
                "condition-B_1.0",
                "condition-C_1.0",
                "condition-D_1.0",
                "condition-E_1.0",
                "condition-F_1.0",
                "condition-G_1.0",
                "condition-H_1.0",
                "condition_1.0",
            ],
            deps2strlist(deps),
        )

    def test_prereq(self):
        apmap = TestApiDepends.MANIFEST_MAP

        self.assertEqual(apmap[PackageIdentifier.parse("prereq-A_1.0")].requires_packages, ["prereq-true_1.0"])
        self.assertEqual(apmap[PackageIdentifier.parse("prereq-C_1.0")].requires_packages, ["prereq-A_1.0", "prereq-B_1.0"])
        self.assertEqual(apmap[PackageIdentifier.parse("prereq-D_1.0")].requires_packages, ["prereq-true_1.0", "prereq-false_1.0"])

    def test_prereq_order(self):
        apmap = TestApiDepends.MANIFEST_MAP
        pi = "prereq-D_1.0"

        prereqs = apmap[PackageIdentifier.parse(pi)].requires_packages
        self.assertEqual(["prereq-true_1.0", "prereq-false_1.0"], prereqs)
        prereqs = DependencyUtils.prereq(PackageIdentifier.parse_list([pi]), apmap, {})
        self.assertEqual(["prereq-false_1.0", "prereq-true_1.0"], list(map(str, map(IDENTIFIER_GETTER, prereqs))))

    def test_latest_strategy(self):
        ipmap = TestApiDepends.MANIFEST_MAP

        deps = DependencyUtils.installed(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), ipmap)
        self.assertEqual(
            ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"],
            list(map(str, map(IDENTIFIER_GETTER, deps))),
        )

        deps = DependencyUtils.installed(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), ipmap, only_keep_latest=True)
        self.assertEqual(["container-C_1.0", "container-D_1.0", "container-A_2.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

    def test_resolve_latest(self):
        pi10 = PackageIdentifier.parse("version_1.0")
        pi20 = PackageIdentifier.parse("version_2.0")

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["testlatest_1.0"]), TestApiDepends.MANIFEST_MAP, {})
        self.assertEqual(["version_2.0", "testlatest_1.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["testlatest_1.0"]), TestApiDepends.MANIFEST_MAP, {pi10: TestApiDepends.MANIFEST_MAP[pi10]})
        self.assertEqual(["version_2.0", "testlatest_1.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["testlatest_1.0"]), TestApiDepends.MANIFEST_MAP, {pi20: TestApiDepends.MANIFEST_MAP[pi20]})
        self.assertEqual(["testlatest_1.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.prereq(PackageIdentifier.parse_list(["testlatest_2.0"]), TestApiDepends.MANIFEST_MAP, {})
        self.assertEqual(["version_2.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.prereq(PackageIdentifier.parse_list(["testlatest_2.0", "testlatest_2.1"]), TestApiDepends.MANIFEST_MAP, {})
        self.assertEqual(["version_2.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

    def test_upgrade(self):
        pi10 = PackageIdentifier.parse("upgrade_1.0")
        pi11 = PackageIdentifier.parse("upgrade_1.1")
        pi12 = PackageIdentifier.parse("upgrade_1.2")

        ideps, udeps = DependencyUtils.upgrade(None, TestApiDepends.MANIFEST_MAP, {pi10: TestApiDepends.MANIFEST_MAP[pi10]})
        self.assertEqual([], [str(mf.identifier) for mf in ideps])
        self.assertEqual([], [str(mf.identifier) for mf in udeps])

        ideps, udeps = DependencyUtils.upgrade(
            None,
            TestApiDepends.MANIFEST_MAP,
            {pi10: TestApiDepends.MANIFEST_MAP[pi10], pi11: TestApiDepends.MANIFEST_MAP[pi11], pi12: TestApiDepends.MANIFEST_MAP[pi12]},
        )
        self.assertEqual(["upgrade_2.0"], [str(mf.identifier) for mf in ideps])
        self.assertEqual(["upgrade_1.1", "upgrade_1.2"], [str(mf.identifier) for mf in udeps])
