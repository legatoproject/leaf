"""
Renderer for search and package list commands

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.model.filtering import PackageFilter
from leaf.model.package import AvailablePackage, ConditionalPackageIdentifier, InstalledPackage, Manifest
from leaf.rendering.alignment import HAlign
from leaf.rendering.formatutils import sizeof_fmt
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class ManifestListRenderer(Renderer):

    """
    Renderer for search and package list commands
    """

    def __init__(self, pkg_filter: PackageFilter = None):
        """
        Store the pkg_filter to show it in the table header
        """
        Renderer.__init__(self)
        self.pkg_filter = pkg_filter

    def _tostring_default(self):
        """
        Show a table like that:
        ┌──────────────────────────────────────────────────┐
        │         4 packages - Filter: only master         │
        ├──────────────────────────┬─────────────┬─────────┤
        │        Identifier        │ Description │   Tags  │
        ╞══════════════════════════╪═════════════╪═════════╡
        │ condition_1.0            │             │ latest  │
        │ container-A_1.0          │ Desc1       │ foo     │
        │ container-A_2.0          │             │ foo,bar │
        └──────────────────────────┴─────────────┴─────────┘
        """
        count = 7
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)
        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Identifier"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Description"), HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Tags"), HAlign.CENTER).new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in self:
                # Draw table
                table.new_row().new_separator().new_cell(element.identifier).new_separator().new_cell(element.description or "").new_separator().new_cell(
                    self._get_tags(element)
                ).new_separator()

            # Footer
            table.new_row().new_separator(count)

        return table

    def _tostring_verbose(self):
        """
        Show a table like that:
        ┌────────────────────────────────────────────────────────────────────────────────┐
        │  47 packages - Filter: only master and (+tag1 or +tag2keyword1 or +keyword2)   │
        ├─────────────────────────────────────┬──────────────────────────────────────────┤
        │              Identifier             │                Properties                │
        ╞═════════════════════════════════════╪══════════════════════════════════════════╡
        │ condition_1.0                       │       Description: None                  │
        │                                     │              Tags: latest                │
        │                                     │              Size: 528 bytes             │
        │                                     │      Release date: 29/12/2015            │
        │                                     │            Source: remote2               │
        │                                     │ Included Packages: condition-A_1.0       │
        │                                     │                    condition-B_1.0       │
        │                                     │                    condition-C_1.0       │
        │                                     │                    condition-D_1.0       │
        │                                     │                    condition-E_1.0       │
        │                                     │                    condition-F_1.0       │
        │                                     │                    condition-G_1.0       │
        │                                     │                    condition-H_1.0       │
        ├─────────────────────────────────────┼──────────────────────────────────────────┤
        │ ...                                 │                ... ...                   │
        """
        count = 6
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Identifier"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Properties"), HAlign.CENTER
            ).new_hspan().new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in self:
                labels, values = self._create_property_table(element)

                # Create table row
                table.new_row().new_separator().new_cell(element.identifier).new_separator().new_cell("\n".join(map(str, labels)), HAlign.RIGHT).new_cell(
                    "\n".join(map(str, values))
                ).new_separator()

                # Footer for each manifest
                table.new_row().new_separator(count)

        return table

    def _create_property_table(self, element):
        labels = []
        values = []

        # Description
        if element.description is not None:
            labels.append("Description:")
            values.append(element.description)

        # Tags
        tag_count = len(element.all_tags)
        if tag_count > 0:
            labels.append("Tag{s}:".format(s=("s" if tag_count > 1 else "")))
            values.append(self._get_tags(element))

        # Release date
        if element.date is not None:
            labels.append("Release date:")
            values.append(element.date)

        # Count included packages
        dependency_count = len(element.depends_packages)

        # For Availables Packages
        if isinstance(element, AvailablePackage):
            # Sources
            remote_count = len(element.remotes)
            if remote_count > 0:
                labels.append("Source{s}:".format(s=("s" if remote_count > 1 else "")))
                values.append(",".join(remote.alias for remote in element.remotes))

            if dependency_count == 0:
                # Size
                labels.append("Size:")
                values.append(sizeof_fmt(element.size))
        # For Installed Packages
        elif isinstance(element, InstalledPackage):
            # Folder
            labels.append("Folder:")
            values.append(element.folder)

        # Included packages
        if dependency_count > 0:
            labels.append("Included Package{s}:".format(s=("s" if dependency_count > 1 else "")))
            values.append("\n".join(self._get_cpis(cpis) for cpis in element.depends_packages))

        return map(self.tm.LABEL, labels), values

    def _add_header_rows(self, table, size):
        """
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────┐
        │                36 packages - Filter: only master                 │
        ├──────────────────────────────────────────────────────────────────┤
        """
        count = len(self)
        title = "{count} {labeltheme}{featureLabel} - Filter:{resettheme} {filter}".format(
            count=count, labeltheme=self.tm.LABEL, featureLabel="packages" if count > 1 else "package", resettheme=self.tm.RESET, filter=self.pkg_filter
        )
        table.new_header(title, size)

    def _get_cpis(self, cpis: str):
        try:
            return str(ConditionalPackageIdentifier.parse(cpis))
        except Exception:
            return cpis

    def _get_tags(self, element: Manifest):
        return ",".join(map(self.tm.colorize_tag, element.all_tags))
