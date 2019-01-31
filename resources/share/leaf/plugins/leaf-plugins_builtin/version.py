
from leaf import __version__
from leaf.cli.plugins import LeafPluginCommand


class VersionPlugin(LeafPluginCommand):

    def _configureParser(self, parser):
        pass

    def execute(self, args, uargs):
        print("leaf version", __version__)
