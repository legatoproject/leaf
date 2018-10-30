'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from tests.testutils import LeafCliWrapper


class TestExtVersion(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testVersion(self):
        self.leafExec("version")
