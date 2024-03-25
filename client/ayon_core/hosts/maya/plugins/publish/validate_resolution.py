import pyblish.api
from ayon_core.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from maya import cmds
from ayon_core.pipeline.publish import RepairAction
from ayon_core.hosts.maya.api import lib
from ayon_core.hosts.maya.api.lib import reset_scene_resolution


class ValidateResolution(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate the render resolution setting aligned with DB"""

    order = pyblish.api.ValidatorOrder
    families = ["renderlayer"]
    hosts = ["maya"]
    label = "Validate Resolution"
    actions = [RepairAction]
    optional = True

    # Colorbleed-edit: Make resolution validation optional
    required_resolution = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid_resolution(instance)
        if invalid:
            raise PublishValidationError(
                "Render resolution is invalid. See log for details.",
                description=(
                    "Wrong render resolution setting. "
                    "Please use repair button to fix it.\n\n"
                    "If current renderer is V-Ray, "
                    "make sure vraySettings node has been created."
                )
            )

    @classmethod
    def get_invalid_resolution(cls, instance):
        width, height, pixelAspect = cls.get_folder_resolution(instance)
        current_renderer = instance.data["renderer"]
        layer = instance.data["renderlayer"]
        invalid = False
        if current_renderer == "vray":
            vray_node = "vraySettings"
            if cmds.objExists(vray_node):
                current_width = lib.get_attr_in_layer(
                    "{}.width".format(vray_node), layer=layer)
                current_height = lib.get_attr_in_layer(
                    "{}.height".format(vray_node), layer=layer)
                current_pixelAspect = lib.get_attr_in_layer(
                    "{}.pixelAspect".format(vray_node), layer=layer
                )
            else:
                cls.log.error(
                    "Can't detect VRay resolution because there is no node "
                    "named: `{}`".format(vray_node)
                )
                return True
        else:
            current_width = lib.get_attr_in_layer(
                "defaultResolution.width", layer=layer)
            current_height = lib.get_attr_in_layer(
                "defaultResolution.height", layer=layer)
            current_pixelAspect = lib.get_attr_in_layer(
                "defaultResolution.pixelAspect", layer=layer
            )
        if current_width != width or current_height != height:
            log_fn = (
                cls.log.error if cls.required_resolution else cls.log.warning
            )
            log_fn(
                "Render resolution {}x{} does not match "
                "folder resolution {}x{}".format(
                    current_width, current_height,
                    width, height
                ))

            # Make resolution validation optional
            if cls.required_resolution:
                invalid = True
        if current_pixelAspect != pixelAspect:
            cls.log.error(
                "Render pixel aspect {} does not match "
                "folder pixel aspect {}".format(
                    current_pixelAspect, pixelAspect
                ))
            invalid = True
        return invalid

    @classmethod
    def get_folder_resolution(cls, instance):
        folder_attributes = instance.data["folderEntity"]["attrib"]
        if (
            "resolutionWidth" in folder_attributes
            and "resolutionHeight" in folder_attributes
            and "pixelAspect" in folder_attributes
        ):
            width = folder_attributes["resolutionWidth"]
            height = folder_attributes["resolutionHeight"]
            pixelAspect = folder_attributes["pixelAspect"]
            return int(width), int(height), float(pixelAspect)

        # Defaults if not found in asset document or project document
        return 1920, 1080, 1.0

    @classmethod
    def repair(cls, instance):
        # Usually without renderlayer overrides the renderlayers
        # all share the same resolution value - so fixing the first
        # will have fixed all the others too. It's much faster to
        # check whether it's invalid first instead of switching
        # into all layers individually
        if not cls.get_invalid_resolution(instance):
            cls.log.debug(
                "Nothing to repair on instance: {}".format(instance)
            )
            return
        layer_node = instance.data['setMembers']
        with lib.renderlayer(layer_node):
            reset_scene_resolution()
