from leaf.cli.plugins import LeafPluginCommand


class BarPlugin(LeafPluginCommand):
    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        self.allow_uargs = True

    def execute(self, args, uargs):
        print("Hello bar", uargs)
        return 0
