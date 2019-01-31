import importlib
import re
from collections import OrderedDict
from enum import Enum
from os import sys
from pathlib import Path

from leaf.cli.cliutils import LeafCommand
from leaf.constants import LeafFiles
from leaf.core.error import printTrace
from leaf.model.package import InstalledPackage, Manifest, PackageIdentifier


class LeafPluginCommand(LeafCommand):
    '''
    Class to inherit from to implement a leaf plugin
    Methods to override are: _configureParser and execute
    '''

    def __init__(self, *args, ip=None, **kwargs):
        LeafCommand.__init__(self, *args, **kwargs)
        self.__installedPackage = ip

    @property
    def installedPackage(self):
        return self.__installedPackage


class PluginScope(Enum):
    BUILTIN = 'builtin'
    USER = 'user'


class LeafPluginManager():

    __INIT__PY = '__init__.py'

    @staticmethod
    def sanitize(o):
        return re.sub(r'[^a-zA-Z0-9_]', '_', str(o)).lower()

    @staticmethod
    def getPluginModuleName(scope: PluginScope, pi: PackageIdentifier, location: str) -> str:
        return '.'.join(map(LeafPluginManager.sanitize,
                            ("leaf", "plugins",
                             scope.value, pi.name, location)))

    def __init__(self):
        self.builtinPluginMap = {}
        self.userPluginMap = {}

    def loadUserPlugins(self, packagesRootFolder: Path):
        self.userPluginMap = self.__loadPluginsFromFolder(
            packagesRootFolder, PluginScope.USER)

    def loadBuiltinPlugins(self, builtinRootFolder: Path):
        self.builtinPluginMap = self.__loadPluginsFromFolder(
            builtinRootFolder, PluginScope.BUILTIN)

    def __listLatestPackages(self, rootFolder: Path):
        latestMap = {}
        # Check folder is valid
        if rootFolder.is_dir():
            # Iterate over all subfolders
            for folder in filter(Path.is_dir, rootFolder.iterdir()):
                # Check manifest exists
                mfFile = folder / LeafFiles.MANIFEST
                if mfFile.is_file():
                    try:
                        ip = InstalledPackage(mfFile)
                        pi = ip.getIdentifier()
                        # Only keep latest version for a given name
                        if pi.name not in latestMap or pi > latestMap[pi.name].getIdentifier():
                            latestMap[pi.name] = ip
                    except BaseException:
                        pass
        return sorted(latestMap.values(), key=Manifest.getIdentifier)

    def __loadPluginsFromFolder(self, folder: Path, scope: PluginScope):
        out = OrderedDict()
        printTrace("Load {} plugins from {}".format(scope.value, folder))
        if folder is not None:
            for ip in self.__listLatestPackages(folder):
                for location, plugin in self.__loadPluginsFromInstalledPackage(ip, scope).items():
                    if location in out:
                        # Plugin already defined, deactivate it
                        out[location] = None
                    else:
                        # New plugin
                        out[location] = plugin
        return out

    def __loadPluginsFromInstalledPackage(self, ip: InstalledPackage, scope: PluginScope) -> tuple:
        out = ip.getPluginMap()
        for location, pluginDef in out.items():
            try:
                # Build the plugin package name
                moduleName = LeafPluginManager.getPluginModuleName(scope,
                                                                   ip.getIdentifier(),
                                                                   location)
                # Load the module
                modules = self.__loadModulesFromPath(pluginDef.getSourceFile(),
                                                     moduleName)
                # Search for the class to instanciate
                cls = self.__findCls(modules,
                                     LeafPluginCommand,
                                     pluginDef.getClassName())
                if cls is not None:
                    # If the class is found, instantiate the command
                    pluginDef.command = cls(pluginDef.name,
                                            pluginDef.getDescription(),
                                            ip=pluginDef.ip)
            except BaseException:
                printTrace("Cannot load plugin {location} from {folder}".format(location=location,
                                                                                folder=ip.folder))
        return out

    def __loadModulesFromPath(self, source: Path, moduleName: str) -> type:
        out = []
        printTrace("[{len}] Load {module}: {path}".format(len=len(sys.modules),
                                                          module=moduleName,
                                                          path=source))
        if source.is_file() and source.suffix == '.py':
            # If source is py file, load it directly
            out.append(self.__loadSpec(source, moduleName))
        elif source.is_dir() and (source / LeafPluginManager.__INIT__PY).is_file():
            # If source is a py folder:
            # Load the __init__.py
            out.append(self.__loadSpec(
                source / LeafPluginManager.__INIT__PY, moduleName))
            # The reccursively load content
            for item in source.iterdir():
                # Do not load __* files
                if not item.name.startswith('__'):
                    subModuleName = "{parent}.{name}".format(parent=moduleName,
                                                             name=re.sub(r'\.py$', '', item.name))
                    out += self.__loadModulesFromPath(item, subModuleName)
        return out

    def __loadSpec(self, pyFile: Path, moduleName: str, force=True):
        # Skip if module already present in sys.modules
        if force or moduleName not in sys.modules:
            if sys.version_info > (3, 5):
                spec = importlib.util.spec_from_file_location(
                    moduleName, str(pyFile))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[moduleName] = module
            else:
                # TODO: Drop this code once python 3.4 is not supported
                loader = importlib.machinery.SourceFileLoader(
                    moduleName, str(pyFile))
                loader.load_module(loader.name)
        return sys.modules[moduleName]

    def __findCls(self, modules: list, expectedCls: type, expectedClsName: str = None):
        for module in modules:
            for _, cls in module.__dict__.items():
                # Check is class
                if not isinstance(cls, type):
                    continue
                # Check class is not imported
                if module.__name__ != cls.__module__:
                    continue
                # Check expected class
                if not issubclass(cls, expectedCls):
                    continue
                # Check expected class name if provided
                if expectedClsName is None or expectedClsName == cls.__name__.split('.')[-1]:
                    return cls

    def getCommands(self, prefix: tuple, ignoredNames: list = None) -> list:
        def isValidPlugin(plugin):
            # Plugin disabled
            if plugin is None:
                return False
            # Instanciation error
            if plugin.command is None:
                return False
            # Check command prefix
            if list(prefix) != plugin.prefix:
                return False
            # Check command is blacklisted
            if ignoredNames is not None and plugin.name in ignoredNames:
                return False
            # Plugin is valid
            return True

        out = OrderedDict()
        # Visit builtin plugins
        if self.builtinPluginMap is not None:
            for _, plugin in self.builtinPluginMap.items():
                if isValidPlugin(plugin):
                    out[plugin.name] = plugin.command
        # Visit user plugins
        if self.userPluginMap is not None:
            for location, plugin in self.userPluginMap.items():
                # prevent user plugin overide builtin plugin
                if location not in self.builtinPluginMap and isValidPlugin(plugin):
                    out[plugin.name] = plugin.command
        return list(out.values())
