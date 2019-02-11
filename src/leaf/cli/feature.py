'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.api import PackageManager
from leaf.cli.cliutils import LeafCommand, initCommonArgs
from leaf.model.features import FeatureManager
from leaf.rendering.renderer.feature import FeatureListRenderer
from leaf.model.base import Scope
from leaf.model.environment import Environment


class FeatureListCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'list',
            "list all available features")

    def execute(self, args, uargs):
        pm = PackageManager()

        featureManager = FeatureManager(pm)
        rend = FeatureListRenderer()
        rend.extend(sorted(featureManager.features.values(),
                           key=lambda x: x.name))
        pm.printRenderer(rend)


class FeatureQueryCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'query',
            "query feature status")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('featureName', metavar='FEATURE',
                            nargs=1,
                            help='the feature name')

    def execute(self, args, uargs):
        pm = PackageManager()

        featureManager = FeatureManager(pm)
        featureName = args.featureName[0]
        feature = featureManager.getFeature(featureName)
        pm.logger.printVerbose("Found feature %s with key %s" %
                               (feature.name, feature.getKey()))

        env = None
        workspace = self.getWorkspaceManager(checkInitialized=False)
        if workspace.isWorkspaceInitialized():
            profile = workspace.getProfile(workspace.getCurrentProfileName())
            env = workspace.getFullEnvironment(profile)
        else:
            env = Environment.build(pm.getBuiltinEnvironment(),
                                    pm.getUserEnvironment())
        envValue = env.findValue(feature.getKey())
        pm.logger.printVerbose("Found %s=%s in env" %
                               (feature.getKey(), envValue))
        featureEnumList = feature.retrieveEnumsForValue(envValue)
        response = ' | '.join(featureEnumList)
        if pm.logger.isQuiet():
            pm.logger.printQuiet(response)
        else:
            pm.logger.printDefault("%s = %s" %
                                   (feature.name, response))


class FeatureToggleCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'toggle',
            "toggle a feature")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser, withScope=True)
        parser.add_argument('featureName', metavar='FEATURE',
                            nargs=1,
                            help='the feature name')
        parser.add_argument('featureValue', metavar='VALUE',
                            nargs=1,
                            help='the feature value')

    def execute(self, args, uargs):
        pm = PackageManager()

        featureManager = FeatureManager(pm)
        name = args.featureName[0]
        value = args.featureValue[0]
        if args.envScope == Scope.USER:
            featureManager.toggleUserFeature(
                name, value, pm)
        elif args.envScope == Scope.WORKSPACE:
            featureManager.toggleWorkspaceFeature(
                name, value, self.getWorkspaceManager())
        elif args.envScope == Scope.PROFILE:
            featureManager.toggleProfileFeature(
                name, value, self.getWorkspaceManager())
