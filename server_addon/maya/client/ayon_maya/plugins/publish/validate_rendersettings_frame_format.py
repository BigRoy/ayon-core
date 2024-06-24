from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    RepairAction,
    ValidateContentsOrder,
)
from ayon_maya.api import lib
from ayon_maya.api import plugin

from maya import cmds


class ValidateRenderSettingsFrameFormat(plugin.MayaInstancePlugin,
                                        OptionalPyblishPluginMixin):
    """Validates the render settings frame format.

    The animation and frame options must be configured as per the
    `required_globals` defined on this plug-in.

    """
    # NOTE: This is a Colorbleed-specific plug-in

    order = ValidateContentsOrder
    label = "Validate Render Settings Frame Format"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [RepairAction]

    _required_globals = {
        "outFormatControl": 0,
        "putFrameBeforeExt": True,
        # 0: No period, 1: Period `.`, 2: Underscore `_`
        "periodInExt": 1,
    }

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                title="Invalid Render Frame Format",
                message=("Invalid render settings found "
                         "for '{}'!".format(instance.name))
            )

    @classmethod
    def get_invalid(cls, instance):
        layer = instance.data['renderlayer']

        node = "defaultRenderGlobals"
        invalid = False
        for attr, required_value in cls._required_globals.items():
            node_attr = f"{node}.{attr}"
            value = lib.get_attr_in_layer(node_attr, layer, as_string=False)
            if value != required_value:
                cls.log.error(f"Render attribute '{attr}' must be "
                              f"{required_value} but is set to {value}.")
                invalid = True

        if invalid:
            return [layer]

    @classmethod
    def repair(cls, instance):
        node = "defaultRenderGlobals"
        for attr, required_value in cls._required_globals.items():
            node_attr = f"{node}.{attr}"
            cmds.setAttr(node_attr, required_value)
