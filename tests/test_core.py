'''
Created on 23 nov. 2017

@author: seb
'''

'''
Constants to tweak the tests
'''

import http
import os
from pathlib import Path
import random
import shutil
import socketserver
from tempfile import mkdtemp
import threading
import unittest
from unittest.case import TestCase

from leaf import LeafConstants, LeafApp, LeafRepository, PackageIdentifier,\
    JsonConstants, LeafUtils


_VERBOSE = True
_ENABLE_HTTP_TESTS = True
_HTTP_FIRST_PORT = 42000


class LeafAppTest():

    PACKAGES = {
        "package-json_1.0.0": '.json',
        "container_1.0.0": '.tar.xz',
        "container_1.2.0": '.tar.xz',
        "package_0.9.9": '.tar.gz',
        "package_1.0.0": '.tar.bz2',
        "package_2.0.0": '.tar.xz',
        "package-deb_1.0.0": '.tar.xz',
        "package-deb_1.0.1": '.tar.xz',
        "package-env_1.0.0": '.tar.xz',
        "package-install_1.0.0": '.tar.xz',
        "package-license_1.0.0": '.tar.xz',
        "package-uninstall_1.0.0": '.tar.xz'}
    PACKAGES_COMPOSITE = {
        "composite-container_1.0.0": '.tar.xz',
        "composite-package_1.0.0": '.tar.xz'}

    @classmethod
    def setUpClass(cls):
        LeafAppTest.ROOT_FOLDER = Path(mkdtemp(prefix="leaf_tests_"))
        #LeafAppTest.ROOT_FOLDER = Path("/tmp/leaf")
        LeafAppTest.REPO_FOLDER = LeafAppTest.ROOT_FOLDER / "repo"
        LeafAppTest.INSTALL_FOLDER = LeafAppTest.ROOT_FOLDER / "app"
        LeafAppTest.CACHE_FOLDER = LeafConstants.CACHE_FOLDER

        shutil.rmtree(str(LeafAppTest.ROOT_FOLDER), True)

        LeafAppTest.doGenerateRepo(
            Path("resources/"), LeafAppTest.REPO_FOLDER)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(LeafAppTest.ROOT_FOLDER), True)

    @staticmethod
    def doGenerateRepo(sourceFolder, outputFolder):
        artifactsFolder = outputFolder / "files"
        artifactsFolder.mkdir(parents=True)

        app = LeafRepository()
        artifacts = []
        for pack, ext in LeafAppTest.PACKAGES_COMPOSITE.items():
            a = artifactsFolder / (pack + ext)
            artifacts.append(a)
            app.pack(sourceFolder / pack / LeafConstants.MANIFEST, a)
        pass
        app.index(outputFolder / "composite.json",
                  artifacts, name="Composite Leaf repository")

        artifacts = []
        for pack, ext in LeafAppTest.PACKAGES.items():
            a = artifactsFolder / (pack + ext)
            artifacts.append(a)
            app.pack(sourceFolder / pack / LeafConstants.MANIFEST, a)
        pass
        app.index(outputFolder / "index.json", artifacts,
                  composites=["composite.json"], name="Master Leaf repository")

    def __init__(self, url):
        self.url = str(url)
        print("Using repo url: " + self.url)

    def getRemoteUrl(self):
        pass

    def setUp(self):
        shutil.rmtree(str(LeafAppTest.INSTALL_FOLDER), ignore_errors=True)
        shutil.rmtree(str(LeafAppTest.CACHE_FOLDER), ignore_errors=True)
        LeafAppTest.INSTALL_FOLDER.mkdir(parents=True)

        self.app = LeafApp(LeafAppTest.INSTALL_FOLDER / "config.json")
        self.app.writeConfiguration(
            {JsonConstants.CONFIG_ROOT: str(LeafAppTest.INSTALL_FOLDER)})
        self.assertEqual(0, len(self.app.listAvailablePackages()))
        self.assertEqual(0, len(self.app.listInstalledPackages()))
        self.assertEqual(0, len(self.app.remoteList()))
        self.app.remoteAdd(self.getRemoteUrl())
        self.assertEqual(1, len(self.app.remoteList()))
        self.app.fetchRemotes()
        self.assertEqual(
            len(LeafAppTest.PACKAGES) + len(LeafAppTest.PACKAGES_COMPOSITE),
            len(self.app.listAvailablePackages()))
        pass

    def tearDown(self):
        shutil.rmtree(str(LeafAppTest.INSTALL_FOLDER), True)
        pass

    def checkContent(self, content, pisList):
        self.assertEqual(len(content), len(pisList))
        for pis in pisList:
            self.assertTrue(PackageIdentifier.fromString(pis) in content)

    def checkExtracted(self, pid, data2HardLink=True):
        folder = LeafAppTest.INSTALL_FOLDER / pid
        self.assertTrue(folder.is_dir())
        self.assertTrue((folder / "data1").is_file())
        self.assertTrue((folder / "folder").is_dir())
        self.assertTrue((folder / "folder" / "data2").is_file())
        self.assertEqual(data2HardLink, (folder / "folder" /
                                         "data2-hardlink").is_file())
        self.assertTrue(
            (folder / "folder" / "data1-symlink").is_symlink())
        return folder

    def testInstallPackage(self):
        packageId = "package_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])
        self.checkExtracted(packageId)

    def testInstallWithLicense(self):
        packageId = "package-license_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE, skipLicenses=True)
        self.checkContent(self.app.listInstalledPackages(), [packageId])

    def testPostinstallError(self):
        packageId = "package_0.9.9"
        with self.assertRaises(Exception):
            self.app.install([packageId], keepFolderOnError=True)
        found = False
        for folder in LeafAppTest.INSTALL_FOLDER.iterdir():
            if folder.name.startswith(packageId):
                self.assertTrue(LeafUtils.isFolderIgnored(folder))
                found = True
                break
        self.assertTrue(found)

    def testInstallWithoutVersion(self):
        # TODO not yet implemented
        packageId = "package_2.0.0"
        self.app.install(["package"], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])
        self.checkExtracted(packageId)

    def testInstallJsonLeaf(self):
        packageId = "package-json_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])

    def testInstallWithSteps(self):
        packageId = "package-install_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])

        folder = self.checkExtracted(packageId, data2HardLink=False)
        self.assertTrue((folder / "postinstall.log").is_file())
        self.assertTrue((folder / "folder2").is_dir())
        self.assertTrue((folder / "folder2" / "data2-symlink").is_symlink())
        self.assertTrue((folder / "data2-copy").is_file())
        self.assertTrue((folder / "downloadedFile").is_file())
        self.assertTrue((folder / "package-env_1.0.0.tar.xz").is_file())
        self.assertTrue((folder / "targetFileFromEnv").is_file())
        with open(str(folder / "targetFileFromEnv"), 'r') as fp:
            content = fp.readlines()
            self.assertEquals(1, len(content))
            # FIXME \n at the end?
            self.assertEquals(str(folder) + "\n", content[0])

    def testInstallValidDeb(self):
        packageId = "package-deb_1.0.1"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])

    def testCannotInstallInvalidDeb(self):
        packageId = "package-deb_1.0.0"
        with self.assertRaises(Exception):
            self.app.install([packageId], verbose=_VERBOSE)
            self.checkContent(self.app.listInstalledPackages(), [])
        # TODO check APT message

    def testForceInstallInvalidDeb(self):
        packageId = "package-deb_1.0.0"
        self.app.install([packageId], forceInstall=True, verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])

    def testUninstall(self):
        packageId = "package-uninstall_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId])
        self.checkExtracted(packageId)
        self.app.uninstall([packageId], verbose=_VERBOSE)
        self.assertTrue(
            (LeafAppTest.INSTALL_FOLDER / "uninstall.log").is_file())
        self.checkContent(self.app.listInstalledPackages(), [])

    def testInstallContainer(self):
        packageId = "container_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(),
                          [packageId, "package_1.0.0"])
        self.checkExtracted(packageId)
        self.checkExtracted("package_1.0.0")

    def testInstallComposite(self):
        packageId = "composite-container_1.0.0"
        self.app.install([packageId], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [packageId,
                                                             "package_1.0.0", "composite-package_1.0.0"])
        self.checkExtracted(packageId)
        self.checkExtracted("composite-package_1.0.0")

    def testCannotUninstallDependencies(self):
        self.app.install(["container_1.0.0"], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [
                          "container_1.0.0", "package_1.0.0"])
        self.app.install(["container_1.2.0"], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), ["container_1.2.0", "container_1.0.0", "package_1.0.0", "package-install_1.0.0", "package-uninstall_1.0.0",
                                                             "package-env_1.0.0", "package-deb_1.0.1"])

        self.app.uninstall(["container_1.0.0"], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), ["container_1.2.0", "package_1.0.0", "package-install_1.0.0", "package-uninstall_1.0.0", "package-env_1.0.0",
                                                             "package-deb_1.0.1"])

        self.app.uninstall(["container_1.2.0"], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), [])

    def testEnv(self):
        self.app.install(["container_1.2.0"], verbose=_VERBOSE)
        self.checkContent(self.app.listInstalledPackages(), ["container_1.2.0", "package_1.0.0", "package-install_1.0.0", "package-uninstall_1.0.0", "package-env_1.0.0",
                                                             "package-deb_1.0.1"])

        env = self.app.getEnv(["container_1.2.0"])
        self.assertEquals(3, len(env))
        value = "%s:%s" % (str(LeafAppTest.INSTALL_FOLDER /
                               "package_1.0.0" /
                               "foo"),
                           str(LeafAppTest.INSTALL_FOLDER /
                               "package-install_1.0.0" /
                               "foo"))
        self.assertEquals(value, env["LEAF_PATH"])
        self.assertEquals("FOO", env["LEAF_ENV"])


@unittest.skipUnless(_ENABLE_HTTP_TESTS, "HTTP tests are disable")
class HttpLeafTest(LeafAppTest, unittest.TestCase):

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        TestCase.setUpClass()
        LeafAppTest.setUpClass()

        os.chdir(str(LeafAppTest.REPO_FOLDER))
        HttpLeafTest.httpPort = _HTTP_FIRST_PORT + random.randint(0, 999)
        handler = http.server.SimpleHTTPRequestHandler
        HttpLeafTest.httpd = socketserver.TCPServer(
            ("", HttpLeafTest.httpPort), handler)

        print("Start http server on port: %d" % HttpLeafTest.httpPort)
        HttpLeafTest.thread = threading.Thread(
            target=HttpLeafTest.httpd.serve_forever)
        HttpLeafTest.thread.setDaemon(True)
        HttpLeafTest.thread.start()

    @classmethod
    def tearDownClass(cls):
        TestCase.tearDownClass()
        LeafAppTest.tearDownClass()

        print("Shutdown http server")
        HttpLeafTest.httpd.shutdown()
        HttpLeafTest.thread.join()

    def getRemoteUrl(self):
        return "http://localhost:%d/index.json" % HttpLeafTest.httpPort


class FileLeafTest(LeafAppTest, unittest.TestCase):

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    def getRemoteUrl(self):
        return (LeafAppTest.REPO_FOLDER / "index.json").as_uri()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'FileLeafTest.testInstallPackage']
    unittest.main()
