# -*- coding: utf-8 -*-
"""Create ``Render`` instance in Maya."""
from maya import cmds

from ayon_core.hosts.maya.api import (
    lib_rendersettings,
    plugin
)
from ayon_core.pipeline import CreatorError
from ayon_core.lib import (
    BoolDef,
    NumberDef,
)


class CreateRenderlayer(plugin.RenderlayerCreator):
    """Create and manages renderlayer product per renderLayer in workfile.

    This generates a single node in the scene which tells the Creator to if
    it exists collect Maya rendersetup renderlayers as individual instances.
    As such, triggering create doesn't actually create the instance node per
    layer but only the node which tells the Creator it may now collect
    the renderlayers.

    """

    identifier = "io.openpype.creators.maya.renderlayer"
    product_type = "renderlayer"
    label = "Render"
    icon = "eye"

    layer_instance_prefix = "render"
    singleton_node_name = "renderingMain"

    render_settings = {}

    @classmethod
    def apply_settings(cls, project_settings):
        cls.render_settings = project_settings["maya"]["render_settings"]

    def create(self, product_name, instance_data, pre_create_data):
        # Only allow a single render instance to exist
        if self._get_singleton_node():
            raise CreatorError("A Render instance already exists - only "
                               "one can be configured.")

        # Apply default project render settings on create
        if self.render_settings.get("apply_render_settings"):
            lib_rendersettings.RenderSettings().set_default_renderer_settings()

        super(CreateRenderlayer, self).create(product_name,
                                              instance_data,
                                              pre_create_data)

    def read_instance_node_overrides(self,
                                     instance_node,
                                     layer,
                                     data):
        """Read active state from the actual rendersetup layer itself"""
        if "active" in data:
            # Backwards compatibility: previously this was stored as data
            #   on the instance node. So if this data is found we assume its
            #   before this active state was read from renderlayers.
            #   We update the renderlayer state to match instance node value
            #   so scenes publish like before - and make sure to remove the
            #   value from the instance node itself.
            self.log.info(
                "Moving 'active' state from instance node "
                "{} to renderlayer {}".format(instance_node, layer.name())
            )
            layer.setRenderable(data["active"])
            if cmds.attributeQuery("active", node=instance_node, exists=True):
                cmds.deleteAttr("{}.active".format(instance_node))

        data["active"] = layer.isRenderable()
        return data

    def imprint_instance_node_data_overrides(self, data, instance):
        """Set active state on the actual rendersetup layer itself"""
        if "active" in data:
            # Set active state to renderlayer
            layer = instance.transient_data["layer"]
            layer.setRenderable(data.pop("active"))

        return data

    def get_instance_attr_defs(self):
        """Create instance settings."""

        return [
            BoolDef("review",
                    label="Review",
                    tooltip="Mark as reviewable",
                    default=True),
            BoolDef("extendFrames",
                    label="Extend Frames",
                    tooltip="Extends the frames on top of the previous "
                            "publish.\nIf the previous was 1001-1050 and you "
                            "would now submit 1020-1070 only the new frames "
                            "1051-1070 would be rendered and published "
                            "together with the previously rendered frames.\n"
                            "If 'overrideExistingFrame' is enabled it *will* "
                            "render any existing frames.",
                    default=False),
            BoolDef("overrideExistingFrame",
                    label="Override Existing Frame",
                    tooltip="Override existing rendered frames "
                            "(if they exist).",
                    default=True),

            # TODO: Should these move to submit_maya_deadline plugin?
            # Tile rendering
            BoolDef("tileRendering",
                    label="Enable tiled rendering",
                    default=False),
            NumberDef("tilesX",
                      label="Tiles X",
                      default=2,
                      minimum=1,
                      decimals=0),
            NumberDef("tilesY",
                      label="Tiles Y",
                      default=2,
                      minimum=1,
                      decimals=0),

            # Additional settings
            BoolDef("convertToScanline",
                    label="Convert to Scanline",
                    tooltip="Convert the output images to scanline images",
                    default=False),
            BoolDef("useReferencedAovs",
                    label="Use Referenced AOVs",
                    tooltip="Consider the AOVs from referenced scenes as well",
                    default=False),

            BoolDef("renderSetupIncludeLights",
                    label="Render Setup Include Lights",
                    default=self.render_settings.get("enable_all_lights",
                                                     False))
        ]
