from maya import cmds

import pyblish.api
from ayon_core.hosts.maya.api.action import SelectInvalidAction
from ayon_core.pipeline.publish import (
    ValidateContentsOrder,
    RepairContextAction,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


def force_delete(node):
    if cmds.objExists(node):
        cmds.lockNode(node, lock=False)
        cmds.delete(node)


class ValidateSceneUnknownNodes(pyblish.api.ContextPlugin,
                                OptionalPyblishPluginMixin):
    """Checks to see if there are any unknown nodes in the scene.

    This often happens if nodes from plug-ins are used but are not available
    on this machine.

    Note: Some studios use unknown nodes to store data on (as attributes)
        because it's a lightweight node.

    This differs from validate no unknown nodes since it checks the
    full scene - not just the nodes in the instance.

    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ["model", "rig", "mayaScene", "look", "renderlayer", "yetiRig"]
    optional = True
    label = "Unknown Nodes"
    actions = [SelectInvalidAction, RepairContextAction]

    @staticmethod
    def get_invalid(context):
        return cmds.ls(type='unknown')

    def process(self, context):
        """Process all the nodes in the instance"""
        if not self.is_active(context.data):
            return

        invalid = self.get_invalid(context)
        if invalid:
            raise PublishValidationError("Unknown nodes found: {0}".format(invalid))

    @classmethod
    def repair(cls, context):

        for node in cls.get_invalid(context):
            try:
                force_delete(node)
            except RuntimeError as exc:
                cls.log.error(exc)
