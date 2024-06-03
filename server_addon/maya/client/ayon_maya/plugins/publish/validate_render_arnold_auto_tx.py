from maya import cmds

import pyblish.api

from ayon_core.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
    PublishValidationError
)

from ayon_core.hosts.maya.api.lib_rendersetup import get_attr_in_layer


class ValidateRenderArnoldAutoTx(pyblish.api.InstancePlugin):
    """Validates Arnold's autogenerate .tx files on render is disabled."""

    order = ValidateContentsOrder
    label = "Arnold Auto-Convert Textures to TX off"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [RepairAction]

    def process(self, instance):

        renderer = instance.data.get("renderer")
        layer = instance.data['setMembers']
        if renderer != "arnold":
            self.log.debug("Skipping auto-convert textures validation because "
                           "renderer is not Arnold. "
                           "Renderer: {}".format(renderer))
            return

        plug = "defaultArnoldRenderOptions.autotx"
        if get_attr_in_layer(plug, layer=layer):
            raise PublishValidationError(
                title="Disable Auto TX",
                message="Arnold Auto TX is enabled. Should be disabled.",
                description=(
                    "## Auto-convert textures to .tx files\n"
                    "Auto-convert of textures to `.tx` files is currently "
                    "enabled, but should be disabled.\n\n"
                    "For farm rendering it is recommended to disable the "
                    "automatic texture conversion. Multiple machines trying "
                    "to generate `.tx` files at the same time will "
                    "have them trying to write the same files simultaneously "
                    "which is both dangerous and slow.\n\n"
                    "As such we enforce auto-converting of textures to `.tx` "
                    "to be disabled when submitting to the farm.\n\n"
                    "### Repair\n"
                    "By clicking repair the setting will be disabled "
                    "in the render settings."
                ))

    @classmethod
    def repair(cls, instance):
        plug = "defaultArnoldRenderOptions.autotx"
        if cmds.getAttr(plug):
            cls.log.info("Disabling {}".format(plug))
            cmds.setAttr(plug, False)
