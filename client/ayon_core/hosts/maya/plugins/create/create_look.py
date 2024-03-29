from ayon_core.hosts.maya.api import (
    plugin
)
from ayon_core.lib import (
    BoolDef,
    EnumDef
)

from maya import cmds
from maya.app.renderSetup.model import renderSetup


def get_legacy_layer_name(layer) -> str:
    """Return legacy render layer name from render setup layer"""
    if hasattr(layer, "legacyRenderLayer"):
        connections = cmds.listConnections(
            "{}.legacyRenderLayer".format(layer.name()),
            type="renderLayer",
            exactType=True,
            source=True,
            destination=False,
            plugs=False
        ) or []
        return next(iter(connections), None)
    else:
        # e.g. for DefaultRenderLayer
        return layer.name()


class CreateLook(plugin.MayaCreator):
    """Shader connections defining shape look"""

    identifier = "io.openpype.creators.maya.look"
    label = "Look"
    product_type = "look"
    icon = "paint-brush"

    make_tx = True
    rs_tex = False

    # Cache in `apply_settings`
    renderlayers = {}

    def apply_settings(self, project_settings):
        super(CreateLook, self).apply_settings(project_settings)

        # Get render setup layers and their legacy names since we use the
        # legacy names to toggle to those layers in the codebase.
        rs = renderSetup.instance()
        renderlayers = [rs.getDefaultRenderLayer()]
        renderlayers.extend(rs.getRenderLayers())
        self.renderlayers = {
            get_legacy_layer_name(layer): layer.name()
            for layer in renderlayers
        }

    def get_instance_attr_defs(self):
        return [
            EnumDef("renderLayer",
                    default="defaultRenderLayer",
                    items=self.renderlayers,
                    label="Renderlayer",
                    tooltip="Renderlayer to extract the look from"),
            BoolDef("maketx",
                    label="Convert textures to .tx",
                    tooltip="Whether to generate .tx files for your textures",
                    default=self.make_tx),
            BoolDef("rstex",
                    label="Convert textures to .rstex",
                    tooltip="Whether to generate Redshift .rstex files for "
                            "your textures",
                    default=self.rs_tex)
        ]

    def get_pre_create_attr_defs(self):
        # Show same attributes on create but include use selection
        defs = super(CreateLook, self).get_pre_create_attr_defs()
        defs.extend(self.get_instance_attr_defs())
        return defs
