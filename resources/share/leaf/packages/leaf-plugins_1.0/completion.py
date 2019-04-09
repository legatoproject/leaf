import subprocess

from leaf.cli.plugins import LeafPluginCommand
from leaf.core.constants import CommonSettings
from leaf.core.error import LeafException
from leaf.core.logger import TextLogger


class CompletionPlugin(LeafPluginCommand):

    __SUPPORTED_SHELLS = ("bash", "zsh", "tcsh")
    __ARGCOMPLETE_BIN = "register-python-argcomplete3"

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-s", "--shell", dest="shell", choices=CompletionPlugin.__SUPPORTED_SHELLS, help="select which shell you want to setup")

    def execute(self, args, uargs):

        # Check argcomplete
        if subprocess.call(["which", CompletionPlugin.__ARGCOMPLETE_BIN], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            raise LeafException(
                "Cannot find argcomplete: {bin}".format(bin=CompletionPlugin.__ARGCOMPLETE_BIN),
                hints=[
                    "You can install argcomplete with 'sudo apt-get install python3-argcomplete'",
                    "or using 'pip install argcomplete' if you are in a virtualenv",
                ],
            )

        # Guess shell if not provided
        shell = args.shell
        if shell is None and CommonSettings.SHELL.is_set():
            shell = CommonSettings.SHELL.as_path().name
        # Check supported shell
        if shell not in CompletionPlugin.__SUPPORTED_SHELLS:
            raise LeafException("Unsupported shell")

        # Print commands
        logger = TextLogger()
        logger.print_default("# Evaluate the following lines to load leaf completion for {shell}".format(shell=shell))
        logger.print_default('# e.g. with: eval "$(leaf completion -q -s {shell})"'.format(shell=shell))
        if shell == "bash":
            logger.print_quiet('eval "$({bin} -s bash leaf)";'.format(bin=CompletionPlugin.__ARGCOMPLETE_BIN))
        elif shell == "zsh":
            logger.print_quiet("autoload bashcompinit;")
            logger.print_quiet("bashcompinit;")
            logger.print_quiet("autoload compinit;")
            logger.print_quiet("compinit;")
            logger.print_quiet('eval "$({bin} -s bash leaf)";'.format(bin=CompletionPlugin.__ARGCOMPLETE_BIN))
        elif shell == "tcsh":
            logger.print_quiet('eval "$({bin} -s tcsh leaf)";'.format(bin=CompletionPlugin.__ARGCOMPLETE_BIN))
