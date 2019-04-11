"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from collections import OrderedDict
from pathlib import Path

from leaf.core.constants import JsonConstants
from leaf.core.error import LeafOutOfDateException
from leaf.core.jsonutils import JsonObject, jlayer_diff, jlayer_update, jloadfile, jwritefile
from leaf.core.logger import print_trace
from leaf.core.utils import CURRENT_LEAF_VERSION, Version
from leaf.model.environment import IEnvProvider
from leaf.model.migration import update_root_folder


class ConfigFileWithLayer(JsonObject):
    def __init__(self, *layers: Path, default_factory=OrderedDict):
        model = None
        for layer in layers:
            if layer is not None and layer.is_file():
                if model is None:
                    model = jloadfile(layer)
                else:
                    jlayer_update(model, jloadfile(layer))
        if model is None:
            model = default_factory()
        JsonObject.__init__(self, model)
        self._check_model()

    def _get_updaters(self) -> tuple:
        return ()

    def _check_model(self):
        """
        Method used to check the model and do mandatory migration
        """
        # Check leaf min version
        if CURRENT_LEAF_VERSION < self.leaf_min_version:
            raise LeafOutOfDateException("Leaf has to be updated to version {min_ver}".format(min_ver=self.leaf_min_version))

        # perform upgrade if needed
        if CURRENT_LEAF_VERSION > self.leaf_min_version:
            # Perform migration
            for update_version, updater in self._get_updaters():
                if update_version is None or self.leaf_min_version < update_version:
                    print_trace("Perform config update: {fnc.__name__} ({update_version})".format(fnc=updater, update_version=update_version))
                    updater(self)

    def write_layer(self, output: Path, previous_layer: Path = None, pp: bool = False):
        # Update last leaf version field
        self.leaf_min_version = str(CURRENT_LEAF_VERSION)
        # Extract layer to write
        data = self.json
        if previous_layer is not None and previous_layer.exists():
            data = jlayer_diff(jloadfile(previous_layer), self.json)
        # Write layer
        jwritefile(output, data, pp=pp)

    @property
    def leaf_min_version(self):
        return Version(self.json.get(JsonConstants.LEAFMINVERSION, "0"))

    @leaf_min_version.setter
    def leaf_min_version(self, version):
        if version is None:
            if JsonConstants.LEAFMINVERSION in self.json:
                del self.json[JsonConstants.LEAFMINVERSION]
        else:
            self.json[JsonConstants.LEAFMINVERSION] = str(version)


class UserConfiguration(ConfigFileWithLayer, IEnvProvider):

    """
    Represent a user configuration
    """

    def __init__(self, *layers):
        ConfigFileWithLayer.__init__(self, *layers)
        IEnvProvider.__init__(self, "user configuration")

    def _get_updaters(self) -> dict:
        return super()._get_updaters() + ((Version("2.0"), update_root_folder),)

    def _getenvmap(self):
        if JsonConstants.CONFIG_ENV not in self.json:
            self.json[JsonConstants.CONFIG_ENV] = OrderedDict()
        return self.json[JsonConstants.CONFIG_ENV]

    @property
    def remotes(self) -> dict:
        if JsonConstants.CONFIG_REMOTES not in self.json:
            self.json[JsonConstants.CONFIG_REMOTES] = OrderedDict()
        return self.json[JsonConstants.CONFIG_REMOTES]


class WorkspaceConfiguration(ConfigFileWithLayer, IEnvProvider):

    """
    Represent a workspace configuration, ie Profiles, env ...
    """

    def __init__(self, *layers):
        ConfigFileWithLayer.__init__(self, *layers)
        IEnvProvider.__init__(self, "workspace")

    def _getenvmap(self):
        if JsonConstants.WS_ENV not in self.json:
            self.json[JsonConstants.WS_ENV] = OrderedDict()
        return self.json[JsonConstants.WS_ENV]

    @property
    def profiles(self):
        if JsonConstants.WS_PROFILES not in self.json:
            self.json[JsonConstants.WS_PROFILES] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILES]


class ConfigContextManager:
    def __init__(self, read_function: callable, write_function: callable):
        self.__read = read_function
        self.__write = write_function
        self.__config = None
        pass

    def __enter__(self):
        self.__config = self.__read()
        return self.__config

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type and not exc_value and not traceback:
            self.__write(self.__config)
