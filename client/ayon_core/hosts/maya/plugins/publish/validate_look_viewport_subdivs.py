import pyblish.api
from maya import cmds

import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import ValidateContentsOrder


class ValidateLookViewportSubdivs(pyblish.api.InstancePlugin):
    """Log a warning if a mesh has Viewport Subdivisions enabled.

    Many renderers use the viewport subdivisions (shortcut '3') to also
    subdivide the mesh at rendertime - against many artist's knowledge.
    It's totally fine, but since that data is not included with the look
    publish we'll warn the user that the published look migth differ.

    This of course will depend on the actual renderer used as well.

    """

    order = ValidateContentsOrder
    families = ['look']
    hosts = ['maya']
    label = 'Look Single Shader Per Shape'
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    # The default connections to check
    def process(self, instance):

        meshes = cmds.ls(instance, type="mesh", long=True)
        if not meshes:
            return

        subdivs = cmds.displaySmoothness(meshes,
                                         query=True,
                                         polygonObject=True)
        invalid = []
        for mesh, subdiv in zip(meshes, subdivs):
            if subdiv > 1:
                invalid.append(mesh)

        if not invalid:
            return

        # For an artist friendly report we report the short name of the
        # transform node
        transforms = cmds.listRelatives(invalid, parent=True, fullPath=True)
        transforms = "\n".join(f"- {transform}"
                               for transform in sorted(transforms))

        self.log.warning(
            "Found meshes with viewport subdivision enabled.\n"
            "Many renderers will subdivide meshes at rendertime if "
            "viewport subdivision is enabled, however the look publish does "
            "not include this. As such, published look may appear different "
            "for:\n{}".format(transforms)
        )
