
from leaf.cli.plugins import LeafPluginCommand


class BarPlugin(LeafPluginCommand):

    def _configureParser(self, parser):
        super()._configureParser(parser)
        self.allowUnknownArgs = True

    def execute(self, args, uargs):
        print("Hello bar", uargs)
        return 0
