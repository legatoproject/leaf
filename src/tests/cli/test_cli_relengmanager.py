'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import json
import os
import time

from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.jsonutils import jsonLoadFile, jsonWriteFile
from leaf.core.utils import computeHash
from tests.testutils import RESOURCE_FOLDER, LeafTestCaseWithCli, checkMime


class TestCliRelengManager(LeafTestCaseWithCli):

    def testPackageCompression(self):
        pkgFolder = RESOURCE_FOLDER / "install_1.0"

        def checkAllCompressions(extension, defaultMime):
            outputFile = self.getWorkspaceFolder() / ("myPackage" + extension)
            for compression, mime in (('-z', 'gzip'),
                                      ('-j', 'x-bzip2'),
                                      ('-J', 'x-xz'),
                                      ('-a', defaultMime)):
                self.leafExec(("build", "pack"),
                              "--output", outputFile,
                              "--input", pkgFolder,
                              '--', compression, '.')
                checkMime(outputFile, mime)

        checkAllCompressions('.bin', 'x-tar')
        checkAllCompressions('.tar', 'x-tar')
        checkAllCompressions('.tar.gz', 'gzip')
        checkAllCompressions('.tar.bz2', 'x-bzip2')
        checkAllCompressions('.tar.xz', 'x-xz')
        checkAllCompressions('.leaf', 'x-tar')

    def testExternalHashFile(self):
        pkgFolder = RESOURCE_FOLDER / "install_1.0"
        outputFile = self.getWorkspaceFolder() / "myPackage.leaf"
        infoFile = self.getWorkspaceFolder() / "myPackage.leaf.info"

        self.leafExec(("build", "pack"),
                      "--no-info",
                      "--output", outputFile,
                      "--input", pkgFolder)
        self.assertTrue(outputFile.exists())
        self.assertFalse(infoFile.exists())

        self.leafExec(("build", "pack"),
                      "--output", outputFile,
                      "--input", pkgFolder)
        self.assertTrue(outputFile.exists())
        self.assertTrue(infoFile.exists())

        self.leafExec(("build", "pack"),
                      "--no-info",
                      "--output", outputFile,
                      "--input", pkgFolder,
                      expectedRc=2)

    def testManifestGeneration(self):
        manifestFile = self.getWorkspaceFolder() / LeafFiles.MANIFEST

        fragmentA = self.getWorkspaceFolder() / "a.json"
        jsonWriteFile(
            fragmentA,
            {"#{LEAF_TEST_VARIABLE}": "#{LEAF_TEST_VARIABLE}", 'a': 1, 'info': {'tags': ['tag1']}})

        fragmentB = self.getWorkspaceFolder() / "b.json"
        jsonWriteFile(
            fragmentB,
            {'a': 2})

        fragmentC = self.getWorkspaceFolder() / "c.json"
        jsonWriteFile(
            fragmentC,
            {'b': True, 'info': {'tags': ['tag2']}})

        try:
            os.environ["LEAF_TEST_VARIABLE"] = "hello"
            self.leafExec(("build", "manifest"),
                          '--output', self.getWorkspaceFolder(),
                          '--append', fragmentA,
                          '--append', fragmentB,
                          '--append', fragmentC,
                          '--env',
                          '--name', "foo",
                          '--version', "1.0",
                          '--description', "lorem ipsum #{LEAF_TEST_VARIABLE}",
                          '--date', "2012-12-12 12:12:12",
                          '--master', "true",
                          '--minver', "0.42",
                          '--requires', "a_1",
                          '--requires', "b_1",
                          '--requires', "a_1",
                          '--depends', "a_1",
                          '--depends', "b_1(FOO=BAR)",
                          '--depends', "a_1",
                          '--tag', 'foo',
                          '--tag', 'bar',
                          '--tag', 'foo',
                          '--upgradable', "true")
        finally:
            del os.environ["LEAF_TEST_VARIABLE"]

        self.assertTrue(manifestFile.exists())
        with open(str(manifestFile), 'r') as fp:
            self.assertEqual({
                'hello': 'hello',
                'a': 2,
                'b': True,
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "foo",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "lorem ipsum hello",
                    JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                    JsonConstants.INFO_MASTER: True,
                    JsonConstants.INFO_LEAF_MINVER: "0.42",
                    JsonConstants.INFO_REQUIRES: ["a_1", "b_1"],
                    JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)"],
                    JsonConstants.INFO_TAGS: ["tag1", "tag2", "foo", "bar"],
                    JsonConstants.INFO_AUTOUPGRADE: True, }},
                json.load(fp))

    def testIndexGeneration(self):
        indexFile = self.getWorkspaceFolder() / "index.json"

        # Build some packages
        self.leafExec(("build", 'pack'),
                      '--output', self.getWorkspaceFolder() / 'a.leaf',
                      '--input', RESOURCE_FOLDER / "install_1.0")
        self.leafExec(("build", 'pack'),
                      '--output', self.getWorkspaceFolder() / 'b.leaf',
                      '--input', RESOURCE_FOLDER / "condition_1.0")

        self.leafExec(("build", 'index'),
                      '--output', indexFile,
                      '--name', "Name",
                      '--description', "Description here",
                      '--prettyprint',
                      self.getWorkspaceFolder() / 'a.leaf')
        self.assertTrue(indexFile.exists())
        self.assertEqual(
            1, len(jsonLoadFile(indexFile)[JsonConstants.REMOTE_PACKAGES]))

        self.leafExec(("build", 'index'),
                      '--output', indexFile,
                      '--name', "Name",
                      '--description', "Description here",
                      '--no-info',
                      self.getWorkspaceFolder() / 'a.leaf',
                      self.getWorkspaceFolder() / 'b.leaf')
        self.assertTrue(indexFile.exists())
        self.assertEqual(
            2, len(jsonLoadFile(indexFile)[JsonConstants.REMOTE_PACKAGES]))

    def testIndexGenerationWithExtraTags(self):
        indexFile1 = self.getWorkspaceFolder() / "index1.json"
        indexFile2 = self.getWorkspaceFolder() / "index2.json"
        pkgFolder = RESOURCE_FOLDER / "container-A_1.0"
        leafFile = self.getWorkspaceFolder() / 'a.leaf'
        tagsFiles = self.getWorkspaceFolder() / 'a.leaf.tags'

        with tagsFiles.open('w') as fp:
            fp.write("foo\n")
            fp.write("bar\n")
            fp.write("  foo  \n")
            fp.write("  bar  \n")
            fp.write("\n")
            fp.write("   \n")
            fp.write("foo\n")
            fp.write("  hello\n")
            fp.write("bar\n")
            fp.write("world  \n")

        # Build some packages
        self.leafExec(("build", 'pack'),
                      '--output', leafFile,
                      '--input', pkgFolder)

        self.leafExec(("build", 'index'),
                      '--output', indexFile1,
                      '--prettyprint',
                      leafFile)
        self.assertTrue(indexFile1.exists())
        self.leafExec(("build", 'index'),
                      '--output', indexFile2,
                      '--no-extra-tags',
                      '--prettyprint',
                      leafFile)
        self.assertTrue(indexFile2.exists())

        self.assertEqual(
            1, len(jsonLoadFile(indexFile1)[JsonConstants.REMOTE_PACKAGES]))
        self.assertEqual(
            1, len(jsonLoadFile(indexFile2)[JsonConstants.REMOTE_PACKAGES]))

        self.assertEqual(["foo",
                          "bar",
                          "hello",
                          "world"],
                         jsonLoadFile(indexFile1)[JsonConstants.REMOTE_PACKAGES][0]['info']['tags'])
        self.assertEqual(["foo"],
                         jsonLoadFile(indexFile2)[JsonConstants.REMOTE_PACKAGES][0]['info']['tags'])

    def testReproductibleBuild(self):
        # Build some packages
        pis = "install_1.0"
        pkgFolder = RESOURCE_FOLDER / pis
        manifest = pkgFolder / LeafFiles.MANIFEST
        self.assertTrue(manifest.exists())

        def touchManifest():
            time.sleep(1)
            os.utime(str(manifest), None)

        def buildPackage(output, args):
            self.leafExec(("build", 'pack'),
                          '-i', pkgFolder,
                          '-o', output,
                          '--no-info',
                          '--', *args)

        for extension, arg, mime in (('tar', '-v', 'x-tar'),
                                     ('bz2', '-j', 'x-bzip2'),
                                     ('xz', '-J', 'x-xz')):
            outputFile1 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                       (pis, extension, 1))
            outputFile2 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                       (pis, extension, 2))
            outputFile3 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                       (pis, extension, 3))
            outputFile4 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                       (pis, extension, 4))

            buildPackage(outputFile1, (arg, '.'))
            touchManifest()
            buildPackage(outputFile2, (arg, '.'))
            touchManifest()
            buildPackage(outputFile3, ('--mtime=2018-11-01 00:00:00',
                                       '--sort=name',
                                       '--owner=0', '--group=0', '--numeric-owner',
                                       arg, '.'))
            touchManifest()
            buildPackage(outputFile4, ('--mtime=2018-11-01 00:00:00',
                                       '--sort=name',
                                       '--owner=0', '--group=0', '--numeric-owner',
                                       arg, '.'))

            checkMime(outputFile1, mime)
            checkMime(outputFile2, mime)
            checkMime(outputFile3, mime)
            checkMime(outputFile4, mime)

            self.assertNotEqual(computeHash(outputFile1),
                                computeHash(outputFile2))
            self.assertNotEqual(computeHash(outputFile1),
                                computeHash(outputFile3))
            self.assertNotEqual(computeHash(outputFile2),
                                computeHash(outputFile3))
            self.assertEqual(computeHash(outputFile3),
                             computeHash(outputFile4))

    def testPackageCustomContent(self):
        pkgFolder = RESOURCE_FOLDER / "install_1.0"
        artifact1 = self.getWorkspaceFolder() / "a.leaf"
        artifact2 = self.getWorkspaceFolder() / "b.leaf"
        self.leafExec(("build", "pack"),
                      "--no-info",
                      "--output", artifact1,
                      "--input", pkgFolder,
                      "--",
                      '--mtime=2018-11-01 00:00:00',
                      '--sort=name',
                      '--owner=0', '--group=0', '--numeric-owner',
                      "-J",
                      ".")

        self.leafExec(("build", "pack"),
                      "--no-info",
                      "--output", artifact2,
                      "--input", pkgFolder,
                      "--",
                      '--mtime=2018-11-01 00:00:00',
                      '--sort=name',
                      '--owner=0', '--group=0', '--numeric-owner',
                      "-J",
                      "manifest.json")

        self.assertGreater(artifact1.stat().st_size,
                           artifact2.stat().st_size)

        # Error cases
        self.leafExec(("build", "pack"),
                      "--no-info",
                      "--output", self.getWorkspaceFolder() / "error.leaf",
                      "--input", pkgFolder,
                      "--",
                      "-v",
                      expectedRc=2)


class TestCliRelengManagerVerbose(TestCliRelengManager):

    def __init__(self, *args, **kwargs):
        TestCliRelengManager.__init__(
            self, *args, verbosity="verbose", **kwargs)


class TestCliRelengManagerQuiet(TestCliRelengManager):

    def __init__(self, *args, **kwargs):
        TestCliRelengManager.__init__(
            self, *args, verbosity="quiet", **kwargs)
