'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''


from leaf.model.environment import Environment
from leaf.model.package import ConditionalPackageIdentifier, PackageIdentifier
from tests.testutils import LeafTestCase


class TestConditions(LeafTestCase):

    def testRegex(self):
        pi = PackageIdentifier.fromString("foo_1.2-beta")

        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta")
        self.assertEqual(pi, cpi)
        self.assertEqual([], cpi.conditions)

        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(FOO=BAR)")
        self.assertEqual(pi, cpi)
        self.assertEqual(['FOO=BAR'], cpi.conditions)

        cpi = ConditionalPackageIdentifier.fromString(
            "foo_1.2-beta(FOO)(!BAR)(FOO=BAR)(FOO!=BAR)(FOO~BaR)(FOO!~BaR)")
        self.assertEqual(pi, cpi)
        self.assertEqual(['FOO',
                          '!BAR',
                          'FOO=BAR',
                          'FOO!=BAR',
                          'FOO~BaR',
                          'FOO!~BaR'], cpi.conditions)

    def testSet(self):
        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(FOO)")
        self.assertEqual(['FOO'], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "1"})
        self.assertTrue(cpi.isOk(env))

    def testUnset(self):
        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(!FOO)")
        self.assertEqual(['!FOO'], cpi.conditions)

        env = Environment("ut", {})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "1"})
        self.assertFalse(cpi.isOk(env))

    def testEqual(self):
        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(FOO=BAR)")
        self.assertEqual(['FOO=BAR'], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "BAR2"})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "BAR"})
        self.assertTrue(cpi.isOk(env))

    def testNotEqual(self):
        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(FOO!=BAR)")
        self.assertEqual(['FOO!=BAR'], cpi.conditions)

        env = Environment("ut", {})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "BAR2"})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "BAR"})
        self.assertFalse(cpi.isOk(env))

    def testContains(self):
        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(FOO~BaR)")
        self.assertEqual(['FOO~BaR'], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO WORLD"})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO BAR WORLD"})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO bar WORLD"})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO bAr WORLD"})
        self.assertTrue(cpi.isOk(env))

    def testNotContains(self):
        cpi = ConditionalPackageIdentifier.fromString("foo_1.2-beta(FOO!~BaR)")
        self.assertEqual(['FOO!~BaR'], cpi.conditions)

        env = Environment("ut", {})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO WORLD"})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO BAR WORLD"})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO bar WORLD"})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "HELLO bAr WORLD"})
        self.assertFalse(cpi.isOk(env))

    def testAnd(self):
        cpi = ConditionalPackageIdentifier.fromString(
            "foo_1.2-beta(FOO)(!BAR)(FOO=BAR)")
        self.assertEqual(['FOO', '!BAR', 'FOO=BAR'], cpi.conditions)

        env = Environment("ut", {})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "1"})
        self.assertFalse(cpi.isOk(env))

        env = Environment("ut", {"FOO": "BAR"})
        self.assertTrue(cpi.isOk(env))

        env = Environment("ut", {"FOO": "BAR",
                                 "BAR": "1"})
        self.assertFalse(cpi.isOk(env))
