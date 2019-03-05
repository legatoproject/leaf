from leaf.cli.plugins import LeafPluginCommand


class PluginBar(LeafPluginCommand):
    def execute(self, args, uargs):
        print("Hello D")
        print_help_message("D")


def print_help_message(a):
    print("Help", a, ";)")
