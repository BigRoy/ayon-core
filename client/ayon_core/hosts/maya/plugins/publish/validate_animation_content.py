import re

import pyblish.api
import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder,
    OptionalPyblishPluginMixin,
    RepairAction,
)

from maya import cmds


class RepairRequiredSets(RepairAction):
    label = "Repair required sets"


class ValidateAnimationContent(pyblish.api.InstancePlugin,
                               OptionalPyblishPluginMixin):
    """Adheres to the content of 'animation' product type

    - Must have collected `out_hierarchy` data.
    - All nodes in `out_hierarchy` must be in the instance.

    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["animation"]
    label = "Animation Content"
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction,
               RepairRequiredSets]
    optional = False

    @classmethod
    def get_invalid(cls, instance):

        out_set = next((i for i in instance.data["setMembers"] if
                        i.endswith("out_SET")), None)
        if not out_set:
            raise PublishValidationError(
                "Instance '%s' has no objectSet named: `out_SET`. "
                "If this instance is an unloaded reference, please load the "
                "reference of the rig or disable this instance for publishing."
                "" % instance.name
            )
        assert 'out_hierarchy' in instance.data, "Missing `out_hierarchy` data"

        out_sets = [node for node in instance if node.endswith("out_SET")]
        if len(out_sets) != 1:
            raise PublishValidationError(
                "Couldn't find exactly one out_SET: {0}".format(out_sets)
            )

        # All nodes in the `out_hierarchy` must be among the nodes that are
        # in the instance. The nodes in the instance are found from the top
        # group, as such this tests whether all nodes are under that top group.

        lookup = set(instance[:])
        invalid = [node for node in instance.data['out_hierarchy'] if
                   node not in lookup]

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Animation content is invalid. See log.")

    @classmethod
    def repair(cls, instance):
        """Try to find out_SET and controls_SET"""

        objset = instance.data["instance_node"]
        references = get_references_in_set(objset)
        references_unique = list(sorted(set(references)))
        if len(references_unique) > 1:
            cls.log.warning("Found more than one reference node: "
                            "{}".format(references_unique))

        # Let's first make sure that the reference is loaded because it being
        # unloaded is usually the cause for this issue
        loaded_references = []
        for ref_node in references_unique:
            if not cmds.referenceQuery(ref_node, isLoaded=True):
                cls.log.info("Loading reference node: {}".format(ref_node))
                cmds.file(loadReference=ref_node)
                loaded_references.append(ref_node)

        def _find_sets(nodes):
            """Find required sets among the given nodes"""
            out_set = None
            controls_set = None
            for node in cmds.ls(nodes, type="objectSet"):
                if out_set is None and node.endswith("out_SET"):
                    out_set = node
                elif controls_set is None and node.endswith("controls_SET"):
                    controls_set = node
                if out_set and controls_set:
                    break
            return out_set, controls_set

        # Check first whether due to any changes in the scene or reference
        # loading above the out_SET and controls_SET started appearing
        set_members = cmds.sets(objset, query=True, nodesOnly=True) or []
        if not all(_find_sets(set_members)):
            if loaded_references:
                cls.log.debug(
                    "Still no out_SET and controls_SET in instance after "
                    "ensuring references are loaded."
                )

            cls.log.debug(
                "Searching for sets in the reference nodes: "
                "{}".format(references_unique)
            )
            processed = set()
            for ref_node in references:
                if ref_node in processed:
                    continue

                ref_members = cmds.referenceQuery(ref_node,
                                                  nodes=True,
                                                  dagPath=True)
                sets = _find_sets(ref_members)
                if all(sets):
                    cls.log.info("Found and adding sets: {}".format(sets))
                    cmds.sets(sets, forceElement=objset)
                    break
                processed.add(ref_node)

        # Remove any placeHolderList entries as a cleanup process
        remove = []
        placeholder_regex = re.compile("^.*\.placeHolderList\[\d+\]$")
        for member in cmds.sets(objset, query=True) or []:
            if placeholder_regex.match(member):
                remove.append(member)
        if remove:
            cls.log.debug(
                "Removing placeHolderList entries: {}".format(remove)
            )
            cmds.sets(remove, remove=objset)


def get_references_in_set(objset):
    """Find related reference nodes for set members.

    1. Detect reference node from a reference's `groupReference' node
    2. Detect any actual reference nodes in the set
        - this includes any 'placeHolderList[]' entries
    3. Detect any reference nodes from referenced nodes in the set.

    Note that it's very likely the resulting list has duplicate entries
    but it's still a `list` to preserve the detected order from the above
    described three steps.

    Returns:
        list: List of reference nodes

    """

    set_members = cmds.sets(objset, query=True, nodesOnly=True) or []
    references = []

    # Usually the root node is in the object set - which is not a
    # referenced node but it is connected to the reference node's
    # `.associatedNode` array attribute
    associated_plug_regex = re.compile("^.*\.associatedNode\[\d+\]$")
    connected_reference_plugs = cmds.listConnections(
        set_members,
        plugs=True,
        destination=True,
        source=False,
        type='reference'
    ) or []
    for plug in connected_reference_plugs:
        if not associated_plug_regex.match(plug):
            continue

        ref_node = plug.split(".", 1)[0]
        if cmds.nodeType(ref_node) != "reference":
            continue

        references.append(ref_node)

    # Find any references from the set members since those usually define
    # the loaded rig instance this animation instance exists for
    references.extend(cmds.ls(set_members, type="reference"))

    # If still no references, allow any of the set members to be
    # a referenced node and takes those reference nodes
    for member in set_members:
        if cmds.referenceQuery(member, isNodeReferenced=True):
            ref_node = cmds.referenceQuery(member, referenceNode=True)
            references.append(ref_node)

    return references
