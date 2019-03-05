"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.model.environment import Environment
from leaf.model.package import ConditionalPackageIdentifier, PackageIdentifier
from tests.testutils import LeafTestCase


class TestConditions(LeafTestCase):
    def test_regex(self):
        pi = PackageIdentifier.parse("foo_1.2-beta")

        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta")
        self.assertEqual(pi, cpi)
        self.assertEqual([], cpi.conditions)

        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO=BAR)")
        self.assertEqual(pi, cpi)
        self.assertEqual(["FOO=BAR"], cpi.conditions)

        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO)(!BAR)(FOO=BAR)(FOO!=BAR)(FOO~BaR)(FOO!~BaR)")
        self.assertEqual(pi, cpi)
        self.assertEqual(["FOO", "!BAR", "FOO=BAR", "FOO!=BAR", "FOO~BaR", "FOO!~BaR"], cpi.conditions)

    def test_set(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO)")
        self.assertEqual(["FOO"], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "1"})
        self.assertTrue(cpi.are_conditions_satified(env))

    def test_unset(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(!FOO)")
        self.assertEqual(["!FOO"], cpi.conditions)

        env = Environment("ut", {})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "1"})
        self.assertFalse(cpi.are_conditions_satified(env))

    def test_equal(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO=BAR)")
        self.assertEqual(["FOO=BAR"], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "BAR2"})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "BAR"})
        self.assertTrue(cpi.are_conditions_satified(env))

    def test_not_equal(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO!=BAR)")
        self.assertEqual(["FOO!=BAR"], cpi.conditions)

        env = Environment("ut", {})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "BAR2"})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "BAR"})
        self.assertFalse(cpi.are_conditions_satified(env))

    def test_contains(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO~BaR)")
        self.assertEqual(["FOO~BaR"], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO WORLD"})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO BAR WORLD"})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO bar WORLD"})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO bAr WORLD"})
        self.assertTrue(cpi.are_conditions_satified(env))

    def test_not_contains(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO!~BaR)")
        self.assertEqual(["FOO!~BaR"], cpi.conditions)

        env = Environment("ut", {})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO WORLD"})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO BAR WORLD"})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO bar WORLD"})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "HELLO bAr WORLD"})
        self.assertFalse(cpi.are_conditions_satified(env))

    def test_and(self):
        cpi = ConditionalPackageIdentifier.parse("foo_1.2-beta(FOO)(!BAR)(FOO=BAR)")
        self.assertEqual(["FOO", "!BAR", "FOO=BAR"], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "1"})
        self.assertFalse(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "BAR"})
        self.assertTrue(cpi.are_conditions_satified(env))

        env = Environment("ut", {"FOO": "BAR", "BAR": "1"})
        self.assertFalse(cpi.are_conditions_satified(env))
