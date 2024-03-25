from maya import cmds
from ayon_core.hosts.maya.api.lib import pairwise
from ayon_core.hosts.maya.api.plugin import get_reference_node

from ayon_core.pipeline import InventoryAction


def get_disallowed_camera_edits(ref):

    # No reference edits are allowed to these attributes
    attributes = {
        "translate", "translateX", "translateY", "translateZ",
        "rotate", "rotateX", "rotateY", "rotateZ",
        "scale", "scaleX", "scaleY", "scaleZ",
        "shear", "shearXY", "shearXZ", "shearYZ",
        "rotateAxis", "rotateAxisX", "rotateAxisY", "rotateAxisZ"
        "rotateOrder", "offsetParentMatrix", "focalLength"
    }

    # Get all connect, disconnect and set value reference edits
    all_edits = set()
    for edit_command in ["connectAttr", "disconnectAttr", "setAttr"]:
        edits = cmds.referenceQuery(ref,
                                    editCommand=edit_command,
                                    editAttrs=True,
                                    editNodes=True,
                                    successfulEdits=True,
                                    failedEdits=False) or []

        if edit_command in {"connectAttr", "disconnectAttr"}:
            # We only care about attributes who are on the destination side of
            # things. It's fine if we connect away from the current reference
            # so we ignore the first attribute for each connect and disconnect
            for src, dest in pairwise(edits):
                all_edits.add(dest)
        else:
            all_edits.update(edits)

    ref_namespace = cmds.referenceQuery(ref, namespace=True)
    ref_namespace = ref_namespace.lstrip(":")

    # Filter to only cameras + transforms
    node_to_types = {}  # cache
    relevant_edits = set()
    for plug in all_edits:
        node, attr = plug.split(".", 1)

        # The reference edits includes the edits for both sides of the edit,
        # so a connectAttr edit could potentially return the edit for a node
        # that doesn't belong to this reference itself. In that case we want
        # to ignore it. We check by namespace of the node.
        namespace = node.rsplit("|", 1)[-1].rsplit(":", 1)[0]
        if namespace != ref_namespace:
            continue

        node_type = node_to_types.get(node, None)
        if node_type is None:
            node_type = cmds.nodeType(node)
            node_to_types[node] = node_type

        if node_type not in {"transform", "camera"}:
            continue

        if attr not in attributes:
            continue

        relevant_edits.add(plug)

    return relevant_edits


def remove_disallowed_camera_edits(ref):
    plugs = get_disallowed_camera_edits(ref)

    if not plugs:
        print(f"Reference is ok: {ref}")
        return

    # Sort the plugs just so the printed log is easier to read for the user
    for plug in sorted(plugs):
        print(f"Removing reference edits to '{plug}' on '{ref}'")
        for edit_command in ["connectAttr", "disconnectAttr", "setAttr"]:
            cmds.referenceEdit(plug,
                               removeEdits=True,
                               editCommand=edit_command,
                               successfulEdits=True,
                               failedEdits=True,
                               onReferenceNode=ref)


class RemoveCameraTransformReferenceEdits(InventoryAction):
    """Remove camera transform reference edits."""

    label = "Remove camera transform reference edits"
    icon = "wrench"
    color = "#d8d8d8"

    @staticmethod
    def is_compatible(container):
        return (
            container.get("loader") == "ReferenceLoader"
            and container.get("name", "").startswith("camera")
        )

    def process(self, containers):

        for container in containers:
            if container["loader"] != "ReferenceLoader":
                print("Not a reference, skipping")
                continue

            node = container["objectName"]
            members = cmds.sets(node, query=True, nodesOnly=True)
            ref_node = get_reference_node(members)
            if ref_node:
                remove_disallowed_camera_edits(ref_node)
