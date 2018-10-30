'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os
import traceback

from tests.testutils import LeafCliWrapper, ROOT_FOLDER


class TestExtHelp(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def setUp(self):
        LeafCliWrapper.setUp(self)
        TestExtHelp.OLD_MANPATH = os.environ.get("MANPATH")
        manDir = ROOT_FOLDER / "resources" / "man"
        self.assertTrue(manDir.is_dir())
        if TestExtHelp.OLD_MANPATH is None:
            os.environ['MANPATH'] = "%s" % (manDir.resolve())
        else:
            os.environ['MANPATH'] = "%s:%s" % (manDir.resolve(),
                                               TestExtHelp.OLD_MANPATH)
        print("Update MANPATH:", os.environ['MANPATH'])

    def tearDown(self):
        if TestExtHelp.OLD_MANPATH is None:
            del os.environ['MANPATH']
        else:
            os.environ['MANPATH'] = TestExtHelp.OLD_MANPATH
        LeafCliWrapper.tearDown(self)

    def testHelp(self):
        try:
            self.leafExec("help", "unknown_page", expectedRc=3)
            self.leafExec("help", "--help")
            self.leafExec("help", "--list")
            self.leafExec("help")
            self.leafExec("help", "setup")
            self.leafExec("help", "setup", "--unknown-arg", expectedRc=2)
        except SystemExit:
            traceback.print_exc()
            self.fail("System exit caught")
