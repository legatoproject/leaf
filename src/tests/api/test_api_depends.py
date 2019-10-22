"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import operator
from collections import OrderedDict

from leaf.core.constants import LeafFiles
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import IDENTIFIER_GETTER, AvailablePackage, InstalledPackage, Manifest, PackageIdentifier
from leaf.model.remote import Remote
from tests.testutils import TEST_REMOTE_PACKAGE_SOURCE, LeafTestCase


def deps2strlist(deps):
    return list(map(str, map(IDENTIFIER_GETTER, deps)))


def filtermap(xxmap, *pislist):
    if pislist is None or len(pislist) == 0:
        return OrderedDict(xxmap)
    out = OrderedDict()
    for pi, item in xxmap.items():
        if str(pi) in pislist:
            out[pi] = item
    return out


APMAP = OrderedDict()
IPMAP = OrderedDict()


class TestApiDepends(LeafTestCase):
    @classmethod
    def setUpClass(cls):
        LeafTestCase.setUpClass()

        for f in sorted(TEST_REMOTE_PACKAGE_SOURCE.iterdir(), key=operator.attrgetter("name")):
            if "failure" in f.name:
                # Skip these packages for tests
                continue
            mffile = f / LeafFiles.MANIFEST
            if mffile.exists():
                try:
                    mf = Manifest.parse(mffile)
                    ip = InstalledPackage(mffile)
                    ap = AvailablePackage({"info": mf.info_node}, remote=Remote("alias", {"url": "https://fake.tld/foo"}))
                    APMAP[mf.identifier] = ap
                    IPMAP[mf.identifier] = ip
                except Exception:
                    pass
        print("Found", len(APMAP), LeafFiles.MANIFEST)

    def test_install(self):
        deps = DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), APMAP, {}, env=Environment())
        self.assertEqual(["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"], deps2strlist(deps))

        deps = DependencyUtils.install(
            PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), APMAP, filtermap(IPMAP, "container-E_1.0"), env=Environment()
        )
        self.assertEqual(["container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"], deps2strlist(deps))

    def test_uninstall(self):

        ipmap = OrderedDict()
        for ap in DependencyUtils.install(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), APMAP, {}):
            ipmap[ap.identifier] = IPMAP[ap.identifier]

        self.assertEqual(
            ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"], deps2strlist(ipmap.values())
        )

        deps = DependencyUtils.uninstall(PackageIdentifier.parse_list(["container-A_1.0"]), ipmap)

        self.assertEqual(["container-A_1.0", "container-B_1.0", "container-E_1.0"], deps2strlist(deps))

    def test_conditional_install(self):
        def _getdeps(env, ipmap):
            return DependencyUtils.install(PackageIdentifier.parse_list(["condition_1.0"]), APMAP, ipmap, env=env)

        env = Environment()
        deps = _getdeps(env, {})
        self.assertEqual(["condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "1"})
        deps = _getdeps(env, {})
        self.assertEqual(["condition-A_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR"})
        deps = _getdeps(env, {})
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2"})
        deps = _getdeps(env, {})
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-F_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2", "HELLO": "wOrlD"})
        deps = _getdeps(env, {})
        self.assertEqual(["condition-A_1.0", "condition-C_1.0", "condition-E_1.0", "condition-G_1.0", "condition_1.0"], deps2strlist(deps))

        env = Environment(content={"FOO": "BAR", "FOO2": "BAR2", "HELLO": "wOrlD"})
        deps = _getdeps(env, filtermap(IPMAP, "condition-C_1.0"))
        self.assertEqual(["condition-A_1.0", "condition-E_1.0", "condition-G_1.0", "condition_1.0"], deps2strlist(deps))

    def test_conditional_tree(self):
        def _getdeps(env):
            return DependencyUtils.install(PackageIdentifier.parse_list(["condition_1.0"]), APMAP, {}, env=env)

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
        prereqs = DependencyUtils.prereq(PackageIdentifier.parse_list(["pkg-with-prereq_1.0"]), APMAP, {})
        self.assertEqual(list(map(str, prereqs)), ["prereq-A_1.0", "prereq-B_1.0"])
        for p in prereqs:
            self.assertTrue(isinstance(p, AvailablePackage))

        prereqs = DependencyUtils.prereq(PackageIdentifier.parse_list(["pkg-with-prereq_1.0"]), APMAP, IPMAP)
        self.assertEqual(list(map(str, prereqs)), ["prereq-A_1.0", "prereq-B_1.0"])
        for p in prereqs:
            self.assertTrue(isinstance(p, InstalledPackage))

        prereqs = DependencyUtils.prereq(PackageIdentifier.parse_list(["pkg-with-prereq_2.0"]), APMAP, {})
        self.assertEqual(list(map(str, prereqs)), ["prereq-A_1.0", "prereq-B_2.0"])

        prereqs = DependencyUtils.prereq(PackageIdentifier.parse_list(["pkg-with-prereq_0.1"]), APMAP, {})
        self.assertEqual(list(map(str, prereqs)), ["prereq-A_0.1-fail"])

        prereqs = DependencyUtils.prereq(PackageIdentifier.parse_list(["pkg-with-deps-with-prereq_1.0"]), APMAP, {})
        self.assertEqual(list(map(str, prereqs)), [])
        install = DependencyUtils.install(PackageIdentifier.parse_list(["pkg-with-deps-with-prereq_1.0"]), APMAP, {})
        prereqs = DependencyUtils.prereq([x.identifier for x in install], APMAP, {})
        self.assertEqual(list(map(str, prereqs)), ["prereq-A_1.0", "prereq-B_1.0"])

    def test_latest_strategy(self):
        deps = DependencyUtils.installed(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), IPMAP)
        self.assertEqual(
            ["container-E_1.0", "container-B_1.0", "container-C_1.0", "container-A_1.0", "container-D_1.0", "container-A_2.0"],
            list(map(str, map(IDENTIFIER_GETTER, deps))),
        )

        deps = DependencyUtils.installed(PackageIdentifier.parse_list(["container-A_1.0", "container-A_2.0"]), IPMAP, only_keep_latest=True)
        self.assertEqual(["container-C_1.0", "container-D_1.0", "container-A_2.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

    def test_resolve_latest(self):

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["testlatest_1.0"]), APMAP, {})
        self.assertEqual(["version_2.0", "testlatest_1.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["testlatest_1.0"]), APMAP, filtermap(IPMAP, "version_1.0"))
        self.assertEqual(["version_2.0", "testlatest_1.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.install(PackageIdentifier.parse_list(["testlatest_1.0"]), APMAP, filtermap(IPMAP, "version_2.0"))
        self.assertEqual(["testlatest_1.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.prereq(PackageIdentifier.parse_list(["testlatest_2.0"]), APMAP, {})
        self.assertEqual(["version_2.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

        deps = DependencyUtils.prereq(PackageIdentifier.parse_list(["testlatest_2.0", "testlatest_2.1"]), APMAP, {})
        self.assertEqual(["version_2.0"], list(map(str, map(IDENTIFIER_GETTER, deps))))

    def test_upgrade(self):
        ideps, udeps = DependencyUtils.upgrade(None, APMAP, filtermap(IPMAP, "upgrade_1.0"))
        self.assertEqual([], [str(mf.identifier) for mf in ideps])
        self.assertEqual([], [str(mf.identifier) for mf in udeps])

        ideps, udeps = DependencyUtils.upgrade(None, APMAP, filtermap(IPMAP, "upgrade_1.0", "upgrade_1.1", "upgrade_1.2"))
        self.assertEqual(["upgrade_2.0"], [str(mf.identifier) for mf in ideps])
        self.assertEqual(["upgrade_1.1", "upgrade_1.2"], [str(mf.identifier) for mf in udeps])

    def test_rdepends(self):

        for mfmap in (IPMAP, APMAP):
            pilist = DependencyUtils.rdepends(PackageIdentifier.parse_list(["condition-A_1.0"]), mfmap)
            self.assertEqual(["condition_1.0"], list(map(str, pilist)))

            pilist = DependencyUtils.rdepends(PackageIdentifier.parse_list(["condition-A_1.0"]), mfmap, env=Environment(None, {}))
            self.assertEqual([], list(map(str, pilist)))

            pilist = DependencyUtils.rdepends(PackageIdentifier.parse_list(["condition-A_1.0"]), mfmap, env=Environment(None, {"FOO": "BAR"}))
            self.assertEqual(["condition_1.0"], list(map(str, pilist)))

            pilist = DependencyUtils.rdepends(PackageIdentifier.parse_list(["condition-B_1.0"]), mfmap, env=Environment(None, {}))
            self.assertEqual(["condition_1.0"], list(map(str, pilist)))

            pilist = DependencyUtils.rdepends(PackageIdentifier.parse_list(["condition-B_1.0"]), mfmap, env=Environment(None, {"FOO": "BAR"}))
            self.assertEqual([], list(map(str, pilist)))

            pilist = DependencyUtils.rdepends(PackageIdentifier.parse_list(["condition-B_1.0"]), {})
            self.assertEqual([], list(map(str, pilist)))
