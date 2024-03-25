from ayon_core.pipeline import InventoryAction
from ayon_core.hosts.maya.tools.mayalookassigner.commands import (
    remove_unused_looks
)


class RemoveUnusedLooks(InventoryAction):
    """Remove containers which seem to be unused look containers"""

    label = "Remove Unused Looks"
    icon = "wrench"
    color = "#d8d8d8"

    @staticmethod
    def is_compatible(container):
        return (
            container.get("loader") == "LookLoader"
        )

    def process(self, containers):
        removed_unused = remove_unused_looks(containers)
        if removed_unused:
            return True
