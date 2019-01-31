'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from tests.testutils import LeafCliWrapper


class TestPluginUpdate(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testUpdate(self):
        self.leafExec(("init"))
        self.leafExec(("profile", "create"), "myprofile")
        self.leafExec(("profile", "config"),
                      "-p", "version_1.0", "-p", "container-A_1.0")
        self.leafExec(("profile", "sync"))

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "version_1.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E",
                                  "version"])

        self.leafExec("update", "-p", "version_2.0")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "version_1.0",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E",
                                  "version"])

        self.leafExec("update", "-p", "container-A_1.1")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-A_1.1",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "version_1.0",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E",
                                  "version"])

        self.leafExec("update")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-A_1.1",
                                     "container-A_2.1",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-D_1.0",
                                     "container-E_1.0",
                                     "version_1.0",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-C",
                                  "container-D",
                                  "version"])
