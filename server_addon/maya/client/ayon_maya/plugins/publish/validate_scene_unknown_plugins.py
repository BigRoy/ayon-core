from maya import cmds

import pyblish.api
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


class ValidateSceneUnknownPlugins(pyblish.api.ContextPlugin,
                                  OptionalPyblishPluginMixin):
    """Checks to see if there are any unknown plugins in the scene.

    This often happens if plug-in requirements were stored with the scene
    but those plug-ins are not available on the current machine.

    Repairing this will remove any trace of that particular plug-in.


    Note: Some studios use unknown nodes to store data on (as attributes)
        because it's a lightweight node.

    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ["model", "rig", "mayaScene", "look", "renderlayer", "yetiRig"]
    optional = True
    label = "Unknown Plug-ins"
    actions = [RepairContextAction]

    ignore = {
        "stereoCamera"
    }

    @classmethod
    def get_invalid(cls):
        plugins = sorted(cmds.unknownPlugin(query=True, list=True) or [])

        # Ignore specific plug-ins allowed to be unknown
        plugins = [plugin for plugin in plugins if plugin not in cls.ignore]

        return plugins

    def process(self, context):
        """Process all the nodes in the instance"""
        if not self.is_active(context.data):
            return

        invalid = self.get_invalid()
        if invalid:
            raise PublishValidationError(
                "{} unknown plug-ins found: {}".format(len(invalid), invalid))

    @classmethod
    def repair(cls, context):

        for plugin in cls.get_invalid():
            cls.log.debug("Removing unknown plugin: %s .." % plugin)

            for node in cmds.ls(type="unknown"):
                if not cmds.objExists(node):
                    # Might have been deleted in previous iteration
                    cls.log.debug("Already deleted: {}".format(node))
                    continue

                if cmds.unknownNode(node, query=True, plugin=True) != plugin:
                    continue

                nodetype = cmds.unknownNode(node,
                                            query=True,
                                            realClassName=True)
                cls.log.info("Deleting %s (type: %s)", node, nodetype)

                try:
                    force_delete(node)
                except RuntimeError as exc:
                    cls.log.error(exc)

            # TODO: Remove datatypes
            # datatypes = cmds.unknownPlugin(plugin,
            #                                query=True, dataTypes=True)

            try:
                cmds.unknownPlugin(plugin, remove=True)
            except RuntimeError as exc:
                cls.log.warning(
                    "Failed to remove plug-in %s: %s", plugin, exc)
