from leaf.cli.plugins import LeafPluginCommand


class PluginA(LeafPluginCommand):
    def execute(self, args, uargs):
        print("Hello A")


class PluginB(LeafPluginCommand):
    def execute(self, args, uargs):
        print("Hello B")
