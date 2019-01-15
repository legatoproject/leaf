'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse

from leaf.cli.cliutils import LeafCommand
from leaf.core.coreutils import VariableResolver, executeCommand
from leaf.core.dependencies import DependencyUtils
from leaf.core.error import LeafException
from leaf.format.logger import Verbosity
from leaf.format.renderer.entrypoint import EntrypointListRenderer
from leaf.model.environment import Environment
from leaf.model.package import Manifest, PackageIdentifier


class RunCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'run',
            "execute binary provided by installed packages",
            allowUnknownArgs=True,
            addVerboseQuietArgs=False)

    def _getExamples(self):
        return [("leaf %s" % self.name, "List all declared commands"),
                ("leaf %s myCommand -- --help" % self.name, "See help of a given binary")]

    def _configureParser(self, parser):
        parser.add_argument('-p', '--package',
                            dest='package',
                            metavar='PKG_IDENTIFIER',
                            type=PackageIdentifier.fromString,
                            help="search binary in specified package")
        parser.add_argument('--oneline',
                            action='store_true',
                            help="quiet output when listing available binaries")
        parser.add_argument('binary',
                            metavar='BINARY_NAME',
                            nargs=argparse.OPTIONAL,
                            help='name of binary to execute')

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args, checkInitialized=False)

        ipMap = wm.listInstalledPackages()
        searchingIpList = None
        env = None

        if args.package is not None:
            # User forces the package
            env = Environment.build(wm.getBuiltinEnvironment(),
                                    wm.getUserEnvironment())
            searchingIpList = DependencyUtils.installed([args.package],
                                                        ipMap,
                                                        env=env)
            env.addSubEnv(wm.getPackagesEnvironment(searchingIpList))
        elif wm.isWorkspaceInitialized():
            # We are in a workspace, use the current profile
            profileName = wm.getCurrentProfileName()
            profile = wm.getProfile(profileName)
            wm.isProfileSync(profile, raiseIfNotSync=True)
            searchingIpList = wm.getProfileDependencies(profile)
            env = wm.getFullEnvironment(profile)
        else:
            # Use installed packages
            searchingIpList = sorted(ipMap.values(),
                                     key=Manifest.getIdentifier)

        # Execute
        if args.binary is None:
            # Print mode
            scope = 'installed packages'
            if args.package is not None:
                scope = args.package
            elif wm.isWorkspaceInitialized():
                scope = 'workspace'
            rend = EntrypointListRenderer(scope)
            rend.extend(searchingIpList)
            wm.printRenderer(rend,
                             verbosity=Verbosity.QUIET if args.oneline else Verbosity.DEFAULT)
        elif args.oneline:
            # User gave BIN and --oneline
            raise LeafException("You must specify a binary or '--oneline', not both",
                                hints=["Run 'leaf run --oneline' to list all binaries",
                                       "Run 'leaf run %s -- --oneline %s' pass --oneline to the binary" % (args.binary, ' '.join(uargs))])
        else:
            # Search entry point
            candidateIp = None
            for ip in searchingIpList:
                if args.binary in ip.getBinMap():
                    if candidateIp is None:
                        candidateIp = ip
                    elif candidateIp.getName() != ip.getName():
                        raise LeafException(
                            "Binary %s is declared by multiple packages" % args.binary)
                    elif ip.getIdentifier() > candidateIp.getIdentifier():
                        candidateIp = ip
            if candidateIp is None:
                raise LeafException("Cannot find binary %s" % args.binary)

            if env is None:
                env = Environment.build(wm.getBuiltinEnvironment(),
                                        wm.getUserEnvironment())
                env.addSubEnv(wm.getPackagesEnvironment(DependencyUtils.installed([candidateIp.getIdentifier()],
                                                                                  ipMap,
                                                                                  env=env)))

            ep = candidateIp.getBinMap()[args.binary]
            vr = VariableResolver(candidateIp, ipMap.values())
            return executeCommand(vr.resolve(ep.getCommand()), *uargs,
                                  displayStdout=True,
                                  env=env,
                                  shell=ep.runInShell())
