from leaf import __version__
from leaf.cli.plugins import LeafPluginCommand


class VersionPlugin(LeafPluginCommand):
    def execute(self, args, uargs):
        print("leaf version {version}".format(version=__version__))
