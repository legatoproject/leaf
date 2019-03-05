from leaf.cli.plugins import LeafPluginCommand


class FooPlugin(LeafPluginCommand):
    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        self.allow_uargs = True

    def execute(self, args, uargs):
        print("Hello foo", uargs)
        return 0
