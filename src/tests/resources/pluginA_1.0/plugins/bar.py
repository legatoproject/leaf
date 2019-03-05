from leaf.cli.plugins import LeafPluginCommand


class MyPluginBar(LeafPluginCommand):
    def execute(self, *args, **uargs):
        return 1
