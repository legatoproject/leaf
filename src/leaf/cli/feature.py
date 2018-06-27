'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafMetaCommand, LeafCommand, initCommonArgs
from leaf.core.features import FeatureManager
from leaf.model.base import Scope
from leaf.model.environment import Environment
from leaf.utils import findWorkspaceRoot


class FeatureMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(
            self,
            "feature",
            "manage features from available packages")

    def getDefaultSubCommand(self):
        return FeatureListCommand()

    def getSubCommands(self):
        return [FeatureToggleCommand(),
                FeatureQueryCommand()]


class FeatureListCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "list",
            "list all available features")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)

    def execute(self, args):
        logger = self.getLogger(args)
        packageManager = self.getPackageManager(args)
        featureManager = FeatureManager(packageManager)
        for feature in sorted(featureManager.features.values(),
                              key=lambda x: x.name):
            logger.displayItem(feature)


class FeatureQueryCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "query",
            "query feature status")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)
        parser.add_argument('featureName', metavar='FEATURE',
                            nargs=1,
                            help='the feature name')

    def execute(self, args):
        logger = self.getLogger(args)
        packageManager = self.getPackageManager(args)
        featureManager = FeatureManager(packageManager)
        featureName = args.featureName[0]
        feature = featureManager.getFeature(featureName)
        logger.printVerbose("Found feature %s with key %s" %
                            (feature.name, feature.getKey()))

        env = None
        workspace = self.getWorkspace(args, checkInitialized=False)
        if workspace.isInitialized():
            profile = workspace.getProfile(workspace.getCurrentProfileName())
            env = workspace.getFullEnvironment(profile)
        else:
            env = Environment.build(packageManager.getLeafEnvironment(),
                                    packageManager.getUserEnvironment())
        envValue = env.findValue(feature.getKey())
        logger.printVerbose("Found %s=%s in env" %
                            (feature.getKey(), envValue))
        featureEnumList = feature.retrieveEnumsForValue(envValue)
        response = ' | '.join(featureEnumList)
        if logger.isQuiet():
            logger.printQuiet(response)
        else:
            logger.printDefault("%s = %s" %
                                (feature.name, response))


class FeatureToggleCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "toggle",
            "toggle a feature")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)
        initCommonArgs(parser, withScope=True)
        parser.add_argument('featureName', metavar='FEATURE',
                            nargs=1,
                            help='the feature name')
        parser.add_argument('featureValue', metavar='VALUE',
                            nargs=1,
                            help='the feature value')

    def execute(self, args):
        packageManager = self.getPackageManager(args)
        featureManager = FeatureManager(packageManager)
        name = args.featureName[0]
        value = args.featureValue[0]
        if args.envScope == Scope.USER:
            featureManager.toggleUserFeature(
                name, value, packageManager)
        elif args.envScope == Scope.WORKSPACE:
            featureManager.toggleWorkspaceFeature(
                name, value, self.getWorkspace(args))
        elif args.envScope == Scope.PROFILE:
            featureManager.toggleProfileFeature(
                name, value, self.getWorkspace(args))
