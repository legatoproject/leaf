from leaf.cli.plugins import LeafPluginCommand
from .d import print_help_message
from .mylib.customlib import print_lib_message


class PluginC(LeafPluginCommand):
    def execute(self, args, uargs):
        print("Hello C")
        print_help_message("C")
        print_lib_message("C")
