from leaf.cli.plugins import LeafPluginCommand
from .d import printHelpMessage
from .mylib.customlib import printLibMessage


class PluginC(LeafPluginCommand):

    def execute(self, args, uargs):
        print("Hello C")
        printHelpMessage("C")
        printLibMessage("C")
