"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from collections import OrderedDict
from pathlib import Path

from leaf import __version__
from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.jsonutils import JsonObject, jlayer_diff, jlayer_update, jloadfile, jwritefile
from leaf.core.utils import check_leaf_min_version
from leaf.model.environment import IEnvProvider


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

    def _check_model(self):
        """
        Method used to check the model and do mandatory migration
        """
        pass

    def write_layer(self, output: Path, previous_layer: Path = None, pp: bool = False):
        data = self.json
        if previous_layer is not None and previous_layer.exists():
            data = jlayer_diff(jloadfile(previous_layer), self.json)
        jwritefile(output, data, pp=pp)


class UserConfiguration(ConfigFileWithLayer, IEnvProvider):

    """
    Represent a user configuration
    """

    def __init__(self, *layers):
        ConfigFileWithLayer.__init__(self, *layers)
        IEnvProvider.__init__(self, "user configuration")

    def _check_model(self):
        super()._check_model()
        # Check that all remotes have an URL
        if JsonConstants.CONFIG_REMOTES in self.json:
            remotes = self.json[JsonConstants.CONFIG_REMOTES]
            for alias in [alias for alias, value in remotes.items() if JsonConstants.CONFIG_REMOTE_URL not in value]:
                del remotes[alias]

    def _getenvmap(self):
        if JsonConstants.CONFIG_ENV not in self.json:
            self.json[JsonConstants.CONFIG_ENV] = OrderedDict()
        return self.json[JsonConstants.CONFIG_ENV]

    @property
    def remotes(self) -> dict:
        if JsonConstants.CONFIG_REMOTES not in self.json:
            self.json[JsonConstants.CONFIG_REMOTES] = OrderedDict()
        return self.json[JsonConstants.CONFIG_REMOTES]

    @property
    def install_folder(self) -> Path:
        if JsonConstants.CONFIG_ROOT in self.json:
            return Path(self.json[JsonConstants.CONFIG_ROOT])
        # Default value
        return LeafFiles.DEFAULT_LEAF_ROOT

    @install_folder.setter
    def install_folder(self, folder: Path):
        self.json[JsonConstants.CONFIG_ROOT] = str(folder)


class WorkspaceConfiguration(ConfigFileWithLayer, IEnvProvider):

    """
    Represent a workspace configuration, ie Profiles, env ...
    """

    def __init__(self, *layers):
        ConfigFileWithLayer.__init__(self, *layers)
        IEnvProvider.__init__(self, "workspace")

    def _check_model(self):
        check_leaf_min_version(self.jsonget(JsonConstants.INFO_LEAF_MINVER), exception_message="Leaf has to be updated to work with this workspace")
        self.json[JsonConstants.INFO_LEAF_MINVER] = __version__

    def _getenvmap(self):
        if JsonConstants.WS_ENV not in self.json:
            self.json[JsonConstants.WS_ENV] = OrderedDict()
        return self.json[JsonConstants.WS_ENV]

    @property
    def profiles(self):
        if JsonConstants.WS_PROFILES not in self.json:
            self.json[JsonConstants.WS_PROFILES] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILES]
