'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse

from leaf.api import PackageManager
from leaf.api.remotes import LeafSettings
from leaf.cli.cliutils import LeafCommand, initCommonArgs
from leaf.model.dependencies import DependencyUtils
from leaf.core.error import ProfileOutOfSyncException
from leaf.rendering.renderer.environment import EnvironmentRenderer
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.core.utils import envListToMap


class EnvPrintCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'print',
            "display all environment variables to use the current (or given) profile")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, withEnvScripts=True)
        parser.add_argument('profiles',
                            nargs=argparse.OPTIONAL,
                            metavar='PROFILE',
                            help='the profile name')

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(checkInitialized=False)

        env = None
        if not wm.isWorkspaceInitialized():
            env = Environment.build(
                wm.getBuiltinEnvironment(),
                wm.getUserEnvironment())
        else:
            # Get profile name, key could not exist if command is default
            # command
            name = args.profiles if "profiles" in vars(
                args) and args.profiles is not None else wm.getCurrentProfileName()
            profile = wm.getProfile(name)
            if not wm.isProfileSync(profile):
                raise ProfileOutOfSyncException(profile)
            env = wm.getFullEnvironment(profile)
        wm.printRenderer(EnvironmentRenderer(env))
        if 'activateScript' in vars(args):
            env.generateScripts(args.activateScript, args.deactivateScript)


class EnvBuiltinCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'builtin',
            "display environment variables exported by leaf application")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, withEnvScripts=True)

    def execute(self, args, uargs):
        pm = PackageManager()

        env = pm.getBuiltinEnvironment()
        pm.printRenderer(EnvironmentRenderer(env))
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvUserCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'user',
            "display and update environment variables exported by user configuration")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, addRemoveEnv=True, withEnvScripts=True)

    def _getEpilogText(self):
        settings = ", ".join(sorted(map(lambda s: s.key,
                                        LeafSettings.values())))
        return "note: \n  You can configure leaf settings with the user environment\n  List of settings: " + settings

    def execute(self, args, uargs):
        pm = PackageManager()

        if args.envAddList is not None or args.envRmList is not None:
            pm.updateUserEnv(setMap=envListToMap(args.envAddList),
                             unsetList=args.envRmList)

        env = pm.getUserEnvironment()
        pm.printRenderer(EnvironmentRenderer(env))
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvWorkspaceCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'workspace',
            "display and update environment variables exported by workspace")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, addRemoveEnv=True, withEnvScripts=True)

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager()

        if args.envAddList is not None or args.envRmList is not None:
            wm.updateWorkspaceEnv(setMap=envListToMap(args.envAddList),
                                  unsetList=args.envRmList)

        env = wm.getWorkspaceEnvironment()
        wm.printRenderer(EnvironmentRenderer(env))
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvProfileCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'profile',
            "display and update environment variables exported by profile")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, addRemoveEnv=True, withEnvScripts=True)
        parser.add_argument('profiles',
                            nargs=argparse.OPTIONAL,
                            metavar='PROFILE',
                            help='the profile name')

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager()

        name = args.profiles if args.profiles is not None else wm.getCurrentProfileName()
        profile = wm.getProfile(name)

        if args.envAddList is not None or args.envRmList is not None:
            profile.updateEnv(setMap=envListToMap(args.envAddList),
                              unsetList=args.envRmList)
            profile = wm.updateProfile(profile)

        env = profile.getEnvironment()
        wm.printRenderer(EnvironmentRenderer(env))
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvPackageCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'package',
            "display environment variables exported by packages")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, withEnvScripts=True)
        parser.add_argument('--nodeps',
                            dest='resolveDeps',
                            action='store_false',
                            help="do not add dependencies environements")
        parser.add_argument(dest='pisList',
                            metavar='PKGID',
                            nargs=argparse.REMAINDER)

    def execute(self, args, uargs):
        pm = PackageManager()

        items = None
        if args.resolveDeps:
            items = DependencyUtils.installed(PackageIdentifier.fromStringList(args.pisList),
                                              pm.listInstalledPackages(),
                                              ignoreUnknown=True)
        else:
            items = PackageIdentifier.fromStringList(args.pisList)
        env = pm.getPackagesEnvironment(items)
        pm.printRenderer(EnvironmentRenderer(env))
        env.generateScripts(args.activateScript, args.deactivateScript)
