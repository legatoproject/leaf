import importlib
import re
from collections import OrderedDict
from enum import Enum
from os import sys
from pathlib import Path

from leaf.cli.base import LeafCommand
from leaf.core.logger import print_trace
from leaf.model.package import InstalledPackage, PackageIdentifier


class LeafPluginCommand(LeafCommand):

    """
    Class to inherit from to implement a leaf plugin
    Methods to override are: _configure_parser and execute
    """

    def __init__(self, *args, ip=None, **kwargs):
        LeafCommand.__init__(self, *args, **kwargs)
        self.__installedPackage = ip

    @property
    def installed_package(self):
        return self.__installedPackage


class PluginScope(Enum):
    BUILTIN = "builtin"
    USER = "user"


class LeafPluginManager:

    __INIT__PY = "__init__.py"

    @staticmethod
    def __sanitize(o):
        return re.sub(r"[^a-zA-Z0-9_]", "_", str(o)).lower()

    @staticmethod
    def __get_plugin_module_name(scope: PluginScope, pi: PackageIdentifier, location: str) -> str:
        return ".".join(map(LeafPluginManager.__sanitize, ("leaf", "plugins", scope.value, pi.name, location)))

    def __init__(self):
        self.__builtin_plugins = {}
        self.__user_plugins = {}

    def load_user_plugins(self, ipmap: dict):
        self.__user_plugins = self.__load_plugins(ipmap, PluginScope.USER)

    def load_builtin_plugins(self, ipmap: dict):
        self.__builtin_plugins = self.__load_plugins(ipmap, PluginScope.BUILTIN)

    def __load_plugins(self, ipmap: dict, scope: PluginScope) -> dict:
        out = OrderedDict()
        for ip in ipmap.values():
            for plugindef in self.__load_plugins_from_installed_package(ip, scope):
                if plugindef.location in out:
                    # Plugin already defined, deactivate it
                    print_trace("Disable plugin {pd.location} declared more than once".format(pd=plugindef))
                    out[plugindef.location] = None
                else:
                    # New plugin
                    out[plugindef.location] = plugindef
        return out

    def __load_plugins_from_installed_package(self, ip: InstalledPackage, scope: PluginScope) -> list:
        out = []
        for _, plugindef in ip.plugins.items():
            out.append(plugindef)
            try:
                # Build the plugin package name
                module_name = LeafPluginManager.__get_plugin_module_name(scope, ip.identifier, plugindef.location)
                # Load the module
                modules = self.__load_modules_from_path(plugindef.source_file, module_name)
                # Search for the class to instanciate
                cls = self.__find_class(modules, LeafPluginCommand, plugindef.classname)
                if cls is not None:
                    # If the class is found, instantiate the command
                    plugindef.command = cls(plugindef.name, plugindef.description, ip=plugindef.installed_package)
            except BaseException:
                print_trace("Cannot load plugin {pd.location} from {ip.folder}".format(pd=plugindef, ip=ip))
        return out

    def __load_modules_from_path(self, source: Path, module_name: str) -> type:
        out = []
        print_trace("Load {module} from {path}".format(module=module_name, path=source))
        if source.is_file() and source.suffix == ".py":
            # If source is py file, load it directly
            out.append(self.__load_spec(source, module_name))
        elif source.is_dir() and (source / LeafPluginManager.__INIT__PY).is_file():
            # If source is a py folder:
            # Load the __init__.py
            out.append(self.__load_spec(source / LeafPluginManager.__INIT__PY, module_name))
            # The reccursively load content
            for item in source.iterdir():
                # Do not load __* files
                if not item.name.startswith("__"):
                    submodule_name = "{parent}.{name}".format(parent=module_name, name=re.sub(r"\.py$", "", item.name))
                    out += self.__load_modules_from_path(item, submodule_name)
        return out

    def __load_spec(self, pyfile: Path, module_name: str, force=True):
        # Skip if module already present in sys.modules
        if force or module_name not in sys.modules:
            if sys.version_info > (3, 5):
                spec = importlib.util.spec_from_file_location(module_name, str(pyfile))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[module_name] = module
            else:
                # TODO: Drop this code once python 3.4 is not supported
                loader = importlib.machinery.SourceFileLoader(module_name, str(pyfile))
                loader.load_module(loader.name)
        return sys.modules[module_name]

    def __find_class(self, modules: list, class_: type, classname: str = None):
        for module in modules:
            for _, cls in module.__dict__.items():
                # Check is class
                if not isinstance(cls, type):
                    continue
                # Check class is not imported
                if module.__name__ != cls.__module__:
                    continue
                # Check expected class
                if not issubclass(cls, class_):
                    continue
                # Check expected class name if provided
                if classname is None or classname == cls.__name__.split(".")[-1]:
                    return cls

    def get_commands(self, prefix: tuple, ignored_names: list = None) -> list:
        def is_valid_plugin(plugin):
            # Plugin disabled
            if plugin is None:
                return False
            # Instanciation error
            if plugin.command is None:
                return False
            # Check command prefix
            if list(prefix)[1:] != plugin.prefix:
                return False
            # Check command is blacklisted
            if ignored_names is not None and plugin.name in ignored_names:
                return False
            # Plugin is valid
            return True

        out = OrderedDict()
        # Visit builtin plugins
        if self.__builtin_plugins is not None:
            for _, plugin in self.__builtin_plugins.items():
                if is_valid_plugin(plugin):
                    out[plugin.name] = plugin.command
        # Visit user plugins
        if self.__user_plugins is not None:
            for location, plugin in self.__user_plugins.items():
                # prevent user plugin overide builtin plugin
                if location not in self.__builtin_plugins and is_valid_plugin(plugin):
                    out[plugin.name] = plugin.command
        return list(out.values())
