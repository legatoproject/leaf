'''
@author: seb
'''

from http.server import SimpleHTTPRequestHandler
from multiprocessing import Process
import os
import socketserver
import sys
import unittest

from tests.test_packagemanager_file import TestPackageManager_File
from tests.utils import AbstractTestWithRepo


# Needed for http server
sys.path.insert(0, os.path.abspath('..'))

HTTP_PORT = os.environ.get("LEAF_HTTP_PORT", "54940")


def startHttpServer(rootFolder):
    print("Start http server for %s on port %s" %
          (rootFolder, HTTP_PORT), file=sys.stderr)
    os.chdir(str(rootFolder))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", int(HTTP_PORT)),
                                   SimpleHTTPRequestHandler)
    httpd.serve_forever()


class TestPackageManager_Http(TestPackageManager_File):

    def __init__(self, methodName):
        TestPackageManager_File.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        TestPackageManager_File.setUpClass()
        print("Using http port %s" % HTTP_PORT, file=sys.stderr)
        TestPackageManager_Http.process = Process(target=startHttpServer,
                                                  args=(AbstractTestWithRepo.REPO_FOLDER,))
        TestPackageManager_Http.process.start()

    @classmethod
    def tearDownClass(cls):
        TestPackageManager_File.tearDownClass()
        print("Stopping http server ...", file=sys.stderr)
        TestPackageManager_Http.process.terminate()
        TestPackageManager_Http.process.join()
        print("Stopping http server ... done", file=sys.stderr)

    def getRemoteUrl(self):
        return "http://localhost:%s/index.json" % HTTP_PORT


if __name__ == "__main__":
    unittest.main()
