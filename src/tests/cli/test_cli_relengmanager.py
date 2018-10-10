'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import json
import os
import tarfile
import unittest

from leaf.constants import JsonConstants, LeafFiles
from leaf.utils import computeHash, jsonWriteFile, jsonLoadFile
from tests.testutils import LEAF_UT_SKIP, LeafCliWrapper, RESOURCE_FOLDER, \
    checkMime


class TestRelengManagerCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testPackageCompression(self):

        pkgFolder = RESOURCE_FOLDER / "install_1.0"

        def checkAllCompressions(extension, defaultMime):
            outputFile = self.getWorkspaceFolder() / ("myPackage" + extension)
            for compression, mime in (('tar', 'x-tar'),
                                      ('gz', 'gzip'),
                                      ('bz2', 'x-bzip2'),
                                      ('xz', 'x-xz')):
                self.leafExec(("repository", "pack"),
                              "--compression", compression,
                              "--output", outputFile,
                              pkgFolder)
                checkMime(outputFile, mime)
            self.leafExec(("repository", "pack"),
                          "--output", outputFile,
                          pkgFolder)
            checkMime(outputFile, defaultMime)

        checkAllCompressions('.bin', 'x-xz')
        checkAllCompressions('.tar', 'x-tar')
        checkAllCompressions('.tar.gz', 'gzip')
        checkAllCompressions('.tar.bz2', 'x-bzip2')
        checkAllCompressions('.tar.xz', 'x-xz')
        checkAllCompressions('.leaf', 'x-xz')

    def testExternalHashFile(self):
        pkgFolder = RESOURCE_FOLDER / "install_1.0"
        outputFile = self.getWorkspaceFolder() / "myPackage.leaf"
        infoFile = self.getWorkspaceFolder() / "myPackage.leaf.info"

        self.leafExec(("repository", "pack"),
                      "--no-info",
                      "--output", outputFile,
                      pkgFolder)
        self.assertTrue(outputFile.exists())
        self.assertFalse(infoFile.exists())

        self.leafExec(("repository", "pack"),
                      "--output", outputFile,
                      pkgFolder)
        self.assertTrue(outputFile.exists())
        self.assertTrue(infoFile.exists())

        self.leafExec(("repository", "pack"),
                      "--no-info",
                      "--output", outputFile,
                      pkgFolder,
                      expectedRc=2)

    def testPackageWithTimestamp(self):
        TIMESTAMP = 946684800

        pkgFolder = RESOURCE_FOLDER / "install_1.0"
        outputFile1 = self.getWorkspaceFolder() / "myPackage1.tar"
        outputFile2 = self.getWorkspaceFolder() / "myPackage2.tar"

        self.leafExec(("repository", "pack"),
                      "--output", outputFile1,
                      pkgFolder)
        self.leafExec(("repository", "pack"),
                      "--timestamp", TIMESTAMP,
                      "--output", outputFile2,
                      pkgFolder)

        self.assertNotEquals(computeHash(outputFile1),
                             computeHash(outputFile2))

        outputFolder1 = self.getWorkspaceFolder() / "extract1"
        with tarfile.TarFile.open(str(outputFile1)) as tf:
            tf.extractall(str(outputFolder1))
        manifestFile1 = outputFolder1 / LeafFiles.MANIFEST
        self.assertTrue(manifestFile1.exists())
        self.assertNotEquals(TIMESTAMP, manifestFile1.stat().st_mtime)

        outputFolder2 = self.getWorkspaceFolder() / "extract2"
        with tarfile.TarFile.open(str(outputFile2)) as tf:
            tf.extractall(str(outputFolder2))
        manifestFile2 = outputFolder2 / LeafFiles.MANIFEST
        self.assertTrue(manifestFile2.exists())
        self.assertEquals(TIMESTAMP, manifestFile2.stat().st_mtime)

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
            self.leafExec(("repository", "manifest"),
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
                          '--requires', "a_1",
                          '--requires', "b_1",
                          '--requires', "a_1",
                          '--depends', "a_1",
                          '--depends', "b_1(FOO=BAR)",
                          '--depends', "a_1",
                          '--tag', 'foo',
                          '--tag', 'bar',
                          '--tag', 'foo')
        finally:
            del os.environ["LEAF_TEST_VARIABLE"]

        self.assertTrue(manifestFile.exists())
        with open(str(manifestFile), 'r') as fp:
            self.assertEquals({
                'hello': 'hello',
                'a': 2,
                'b': True,
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "foo",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "lorem ipsum hello",
                    JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                    JsonConstants.INFO_MASTER: True,
                    JsonConstants.INFO_REQUIRES: ["a_1", "b_1"],
                    JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)"],
                    JsonConstants.INFO_TAGS: ["tag1", "tag2", "foo", "bar"], }},
                json.load(fp))

    def testIndexGeneration(self):
        indexFile = self.getWorkspaceFolder() / "index.json"

        # Build some packages
        self.leafExec(('repository', 'pack'),
                      '--output', self.getWorkspaceFolder() / 'a.leaf',
                      RESOURCE_FOLDER / "install_1.0")
        self.leafExec(('repository', 'pack'),
                      '--output', self.getWorkspaceFolder() / 'b.leaf',
                      RESOURCE_FOLDER / "condition_1.0")

        self.leafExec(('repository', 'index'),
                      '--output', indexFile,
                      '--name', "Name",
                      '--description', "Description here",
                      '--prettyprint',
                      self.getWorkspaceFolder() / 'a.leaf')
        self.assertTrue(indexFile.exists())
        self.assertEquals(
            1, len(jsonLoadFile(indexFile)[JsonConstants.REMOTE_PACKAGES]))

        self.leafExec(('repository', 'index'),
                      '--output', indexFile,
                      '--name', "Name",
                      '--description', "Description here",
                      '--no-info',
                      self.getWorkspaceFolder() / 'a.leaf',
                      self.getWorkspaceFolder() / 'b.leaf')
        self.assertTrue(indexFile.exists())
        self.assertEquals(
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
        self.leafExec(('repository', 'pack'),
                      '--output', leafFile,
                      pkgFolder)

        self.leafExec(('repository', 'index'),
                      '--output', indexFile1,
                      '--prettyprint',
                      leafFile)
        self.assertTrue(indexFile1.exists())
        self.leafExec(('repository', 'index'),
                      '--output', indexFile2,
                      '--no-extra-tags',
                      '--prettyprint',
                      leafFile)
        self.assertTrue(indexFile2.exists())

        self.assertEquals(
            1, len(jsonLoadFile(indexFile1)[JsonConstants.REMOTE_PACKAGES]))
        self.assertEquals(
            1, len(jsonLoadFile(indexFile2)[JsonConstants.REMOTE_PACKAGES]))

        self.assertEquals(["foo",
                           "bar",
                           "hello",
                           "world"],
                          jsonLoadFile(indexFile1)[JsonConstants.REMOTE_PACKAGES][0]['info']['tags'])
        self.assertEquals(["foo"],
                          jsonLoadFile(indexFile2)[JsonConstants.REMOTE_PACKAGES][0]['info']['tags'])


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestPackageManagerCli_Verbose(TestRelengManagerCli_Default):
    def __init__(self, methodName):
        TestRelengManagerCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestPackageManagerCli_Quiet(TestRelengManagerCli_Default):
    def __init__(self, methodName):
        TestRelengManagerCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")
