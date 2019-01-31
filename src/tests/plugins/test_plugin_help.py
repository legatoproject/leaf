'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os

from tests.testutils import ROOT_FOLDER, LeafCliWrapper


class TestPluginHelp(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def setUp(self):
        LeafCliWrapper.setUp(self)
        TestPluginHelp.OLD_MANPATH = os.environ.get("MANPATH")
        manDir = ROOT_FOLDER / "resources" / "man"
        self.assertTrue(manDir.is_dir())
        if TestPluginHelp.OLD_MANPATH is None:
            os.environ['MANPATH'] = "%s" % (manDir.resolve())
        else:
            os.environ['MANPATH'] = "%s:%s" % (manDir.resolve(),
                                               TestPluginHelp.OLD_MANPATH)
        print("Update MANPATH:", os.environ['MANPATH'])

    def tearDown(self):
        if TestPluginHelp.OLD_MANPATH is None:
            del os.environ['MANPATH']
        else:
            os.environ['MANPATH'] = TestPluginHelp.OLD_MANPATH
        LeafCliWrapper.tearDown(self)

    def testHelp(self):
        self.exec("help")
        self.exec("help config")
        self.exec("help unknownpage", expectedRc=3)
        self.exec("help --list")
        self.exec("help -l")
        self.exec("help config --foo", expectedRc=2)
