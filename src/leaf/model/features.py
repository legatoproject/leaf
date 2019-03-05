"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import operator
from collections import OrderedDict

from leaf.core.error import LeafException
from leaf.model.environment import IEnvProvider
from leaf.model.package import Feature


class FeatureManager:

    """
    Class used to manage features
    """

    def __init__(self):
        self.__features = OrderedDict()

    @property
    def features(self):
        return self.__features

    def append_features(self, mflist: list):
        # Sort to ensure same behavior over Python versions
        for mf in sorted(mflist, key=operator.attrgetter("name")):
            # Sort to ensure same behavior over Python versions
            for feature in sorted(mf.features, key=operator.attrgetter("name")):
                if feature.name not in self.__features:
                    self.__features[feature.name] = feature
                else:
                    self.__features[feature.name].add_alias(feature)

    def get_feature(self, name: str) -> Feature:
        if name not in self.__features:
            raise LeafException("Cannot find feature {name}".format(name=name))
        return self.__features[name]

    def toggle_feature(self, name: str, enum: str, env_provider: IEnvProvider):
        feature = self.get_feature(name)
        key = feature.key
        value = feature.get_value(enum)
        if value is not None:
            env_provider.update_environment(set_map={key: value})
        else:
            env_provider.update_environment(unset_list=[key])
