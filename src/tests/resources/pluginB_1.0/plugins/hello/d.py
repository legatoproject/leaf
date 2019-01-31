
from leaf.cli.plugins import LeafPluginCommand


class PluginBar(LeafPluginCommand):

    def execute(self, args, uargs):
        print("Hello D")
        printHelpMessage("D")


def printHelpMessage(a):
    print('Help', a, ";)")
