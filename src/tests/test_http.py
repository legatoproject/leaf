'''
Created on 23 nov. 2017

@author: seb
'''

from http.server import SimpleHTTPRequestHandler
import os
import random
import socketserver
import sys
import threading
import unittest

from tests.test_file import CliTest
from tests.utils import TestWithRepository


# Needed for http server
sys.path.insert(0, os.path.abspath('..'))

_HTTP_FIRST_PORT = 42000


class HttpLeafTest(CliTest):

    def __init__(self, methodName):
        CliTest.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        CliTest.setUpClass()

        os.chdir(str(TestWithRepository.REPO_FOLDER))
        HttpLeafTest.httpPort = _HTTP_FIRST_PORT + random.randint(0, 999)
        handler = SimpleHTTPRequestHandler
        HttpLeafTest.httpd = socketserver.TCPServer(("", HttpLeafTest.httpPort),
                                                    handler)

        print("Start http server on port: %d" % HttpLeafTest.httpPort)
        HttpLeafTest.thread = threading.Thread(
            target=HttpLeafTest.httpd.serve_forever)
        HttpLeafTest.thread.setDaemon(True)
        HttpLeafTest.thread.start()

    @classmethod
    def tearDownClass(cls):
        CliTest.tearDownClass()

        print("Shutdown http server")
        HttpLeafTest.httpd.shutdown()
        HttpLeafTest.thread.join()

    def getRemoteUrl(self):
        return "http://localhost:%d/index.json" % HttpLeafTest.httpPort


if __name__ == "__main__":
    unittest.main()
