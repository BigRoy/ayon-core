import inspect

import pyblish.api

from maya import cmds
from ayon_core.pipeline.publish import (
    context_plugin_should_run,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateCurrentRenderLayerIsRenderable(pyblish.api.ContextPlugin,
                                             OptionalPyblishPluginMixin):
    """Validate if current render layer has a renderable camera.

    There is a bug in Redshift which occurs when the current render layer
    at file open has no renderable camera. The error raised is as follows:

    "No renderable cameras found. Aborting render"

    This error is raised even if that render layer will not be rendered.

    """

    label = "Current Render Layer Has Renderable Camera"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["renderlayer"]
    optional = False

    def process(self, context):
        if not self.is_active(context.data):
            return
        # Workaround bug pyblish-base#250
        if not context_plugin_should_run(self, context):
            return

        cameras = cmds.ls(type="camera", long=True)
        renderable = any(c for c in cameras if cmds.getAttr(c + ".renderable"))
        if not renderable:
            layer = cmds.editRenderLayerGlobals(query=True,
                                                currentRenderLayer=True)
            raise PublishValidationError(
                "Current render layer '{}' has no renderable camera".format(
                    layer
                ),
                description=inspect.getdoc(self)
            )
