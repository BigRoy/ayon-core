import pyblish.api
from ayon_core.pipeline.load import any_outdated_containers
from ayon_core.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)


class ShowInventory(pyblish.api.Action):

    label = "Show Inventory"
    icon = "briefcase"
    on = "failed"

    def process(self, context, plugin):
        from ayon_core.tools.utils import host_tools

        host_tools.show_scene_inventory()


class ValidateContainers(OptionalPyblishPluginMixin,
                         pyblish.api.ContextPlugin):

    """Containers are must be updated to latest version on publish."""

    label = "Validate Outdated Containers"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya", "houdini", "nuke", "harmony", "photoshop", "aftereffects"]
    optional = True
    actions = [ShowInventory]

    def process(self, context):
        if not self.is_active(context.data):
            self.log.warning(
                "Validation of outdated containers is disabled."
            )
            return

        if any_outdated_containers():
            msg = "There are outdated containers in the scene."
            raise PublishXmlValidationError(self, msg)
