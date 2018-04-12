'''
@author: seb
'''

from contextlib import closing
from http.server import SimpleHTTPRequestHandler
from multiprocessing import Process
import os
import socket
import socketserver
import sys
import unittest

from tests.test_packagemanager_file import TestPackageManager_File
from tests.utils import AbstractTestWithRepo


# Needed for http server
sys.path.insert(0, os.path.abspath('..'))


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def startHttpServer(port, rootFolder):
    os.chdir(str(rootFolder))
    httpd = socketserver.TCPServer(("", port),
                                   SimpleHTTPRequestHandler)
    print("Start http server for %s on port %d" %
          (rootFolder, port), file=sys.stderr)
    httpd.serve_forever()


class TestPackageManager_Http(TestPackageManager_File):

    def __init__(self, methodName):
        TestPackageManager_File.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        TestPackageManager_File.setUpClass()
        TestPackageManager_Http.httpPort = find_free_port()
        print("Using http port %d" %
              TestPackageManager_Http.httpPort, file=sys.stderr)
        TestPackageManager_Http.process = Process(target=startHttpServer,
                                                  args=(TestPackageManager_Http.httpPort,
                                                        AbstractTestWithRepo.REPO_FOLDER))
        TestPackageManager_Http.process.start()

    @classmethod
    def tearDownClass(cls):
        TestPackageManager_File.tearDownClass()
        print("Stopping http server ...", file=sys.stderr)
        TestPackageManager_Http.process.terminate()
        TestPackageManager_Http.process.join()
        print("Stopping http server ... done", file=sys.stderr)

    def getRemoteUrl(self):
        return "http://localhost:%d/index.json" % TestPackageManager_Http.httpPort


if __name__ == "__main__":
    unittest.main()
