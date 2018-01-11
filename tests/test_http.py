'''
Created on 23 nov. 2017

@author: seb
'''
'''
Constants to tweak the tests
'''

from http.server import SimpleHTTPRequestHandler
import os
import random
import socketserver
import threading
import unittest
from unittest.case import TestCase

from test_file import LeafAppTest


_HTTP_FIRST_PORT = 42000


class HttpLeafTest(LeafAppTest, unittest.TestCase):

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        TestCase.setUpClass()
        LeafAppTest.setUpClass()

        os.chdir(str(LeafAppTest.REPO_FOLDER))
        HttpLeafTest.httpPort = _HTTP_FIRST_PORT + random.randint(0, 999)
        handler = SimpleHTTPRequestHandler
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


if __name__ == "__main__":
    unittest.main()
