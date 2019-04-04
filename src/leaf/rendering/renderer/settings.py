"""
Renderer for settings list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import operator
import os

from leaf.model.base import Scope
from leaf.model.package import ScopeSetting
from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class SettingsListRenderer(Renderer):

    """
    Renderer for settings list command
    """

    def __init__(self, config_folder, values_map: dict, filter_unset: bool = False):
        Renderer.__init__(self)
        self.__folder = config_folder
        self.__values_map = values_map
        self.__filter_unset = filter_unset

    def _filter(self, setting: ScopeSetting):
        if self.__filter_unset:
            value = self.__values_map.get(setting.identifier)
            return value is not None and value != setting.default
        return True

    def __get_scopes_label(self, setting: ScopeSetting) -> str:
        out = ""
        for s in (Scope.USER, Scope.WORKSPACE, Scope.PROFILE):
            if s in setting.scopes:
                out += s.name[0]
            else:
                out += " "
        return " ".join(out)

    def __get_setting_value(self, setting: ScopeSetting, split_path=False) -> str:
        value = self.__values_map.get(setting.identifier)
        # Handle unset
        if value is None:
            return ""
        # Handle long path list
        if split_path and os.pathsep in value and len(value) > 54:
            value = "{sep}\\\n".format(sep=os.pathsep).join(value.split(os.pathsep))
        return '"{0}"'.format(value)

    def _tostring_quiet(self):
        return "\n".join(map(operator.attrgetter("identifier"), filter(self._filter, self)))

    def _tostring_default(self):
        count = 7
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        # Handle filter
        visible_items = list(filter(self._filter, self))
        if len(visible_items) > 0:

            table.new_row().new_separator().new_cell(self.tm.LABEL("Identifier"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Description"), HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Value"), HAlign.CENTER).new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in visible_items:
                value = self.__get_setting_value(element, split_path=True)
                if value is not None:
                    # Draw table
                    table.new_row().new_separator().new_cell(element.identifier).new_separator().new_cell(element.description or "").new_separator().new_cell(
                        value
                    ).new_separator()

            # Footer
            table.new_row().new_separator(count)

        return table

    def _tostring_verbose(self):
        count = 13
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        # Handle filter
        visible_items = list(filter(self._filter, self))
        if len(visible_items) > 0:

            table.new_row().new_separator().new_cell(self.tm.LABEL("Identifier"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Description"), HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Key"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Value"), HAlign.CENTER
            ).new_separator().new_cell(
                self.tm.LABEL("Validator"), HAlign.CENTER
            ).new_separator().new_cell(
                self.tm.LABEL("Scope"), HAlign.CENTER
            ).new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in visible_items:
                value = self.__get_setting_value(element, split_path=True)
                if value is not None:
                    table.new_row().new_separator().new_cell(element.identifier).new_separator().new_cell(element.description or "").new_separator().new_cell(
                        element.key
                    ).new_separator().new_cell(value).new_separator().new_cell(element.is_valid).new_separator().new_cell(
                        self.__get_scopes_label(element)
                    ).new_separator()

            # Footer for each manifest
            table.new_row().new_separator(count)

        return table

    def _add_header_rows(self, table, size):
        title = "{labeltheme}Configuration folder: {folder}{resettheme}".format(labeltheme=self.tm.LABEL, folder=self.__folder, resettheme=self.tm.RESET)
        table.new_header(title, size)
