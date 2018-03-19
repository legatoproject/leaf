'''
@author: seb
'''

from http.server import SimpleHTTPRequestHandler
from multiprocessing import Process
import os
import random
import socketserver
import sys
import unittest

from tests.test_packagemanager_file import TestPackageManager_File
from tests.utils import TestWithRepository


# Needed for http server
sys.path.insert(0, os.path.abspath('..'))

_HTTP_FIRST_PORT = 42000


def startHttpServer(port, rootFolder):
    os.chdir(str(rootFolder))
    httpd = socketserver.TCPServer(("", port),
                                   SimpleHTTPRequestHandler)
    print("Start http server for %s on port %d" % (rootFolder, port))
    httpd.serve_forever()


class TestPackageManager_Http(TestPackageManager_File):

    def __init__(self, methodName):
        TestPackageManager_File.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        TestPackageManager_File.setUpClass()
        TestPackageManager_Http.httpPort = _HTTP_FIRST_PORT + \
            random.randint(0, 999)
        TestPackageManager_Http.process = Process(target=startHttpServer,
                                                  args=(TestPackageManager_Http.httpPort, TestWithRepository.REPO_FOLDER))
        print("Starting http server ...")
        TestPackageManager_Http.process.start()

    @classmethod
    def tearDownClass(cls):
        TestPackageManager_File.tearDownClass()
        print("Stopping http server ...")
        TestPackageManager_Http.process.terminate()
        TestPackageManager_Http.process.join()
        print("Stopping http server ... done")

    def getRemoteUrl(self):
        return "http://localhost:%d/index.json" % TestPackageManager_Http.httpPort


if __name__ == "__main__":
    unittest.main()
