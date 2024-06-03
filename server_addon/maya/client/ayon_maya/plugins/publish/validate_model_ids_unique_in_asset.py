import inspect
from collections import defaultdict

import pyblish.api

from ayon_core.hosts.maya.api import lib
import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)

from maya import cmds


def get_instance_node_ids(instance, ignore_intermediate_objects=True):
    instance_members = cmds.ls(instance,
                               noIntermediate=ignore_intermediate_objects,
                               type=("transform", "shape"),
                               long=True)

    # Collect each id with their members
    ids = defaultdict(list)
    for member in instance_members:
        object_id = lib.get_id(member)
        if not object_id:
            continue
        ids[object_id].append(member)

    return ids


def get_instance_families(instance: pyblish.api.Instance) -> set[str]:
    """Get the instance's families"""
    families = instance.data.get("families", [])
    family = instance.data.get("family")
    if family:
        families.append(family)
    return set(families)


class ValidateNodeIdsUniqueInstanceClash(pyblish.api.InstancePlugin,
                                         OptionalPyblishPluginMixin):
    """## Clashing node ids across model instances

    Validate nodes across model instances have a unique Colorbleed Id

    This validates whether the node ids to be published are unique across
    all model instances currently being published (even if those other
    instances are DISABLED currently for publishing).

    This will *NOT* validate against previous publishes or publishes being
    done from another scene than the current one. It will only validate for
    models that are being published from a single scene.

    """

    order = pyblish.api.ValidatorOrder - 0.1
    label = 'Clashing node ids across model instances'
    hosts = ['maya']
    families = ["model"]
    optional = True

    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction,
               ayon_core.hosts.maya.api.action.GenerateUUIDsOnInvalidAction]

    @classmethod
    def apply_settings(cls, project_settings):
        # Disable plug-in if cbId workflow is disabled
        if not project_settings["maya"].get("use_cbid_workflow", True):
            cls.enabled = False
            return

    def process(self, instance):
        """Process all meshes"""
        if not self.is_active(instance.data):
            return

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                message="Found nodes between different model instances that "
                        "share the same `cbId`.",
                description=inspect.cleandoc(self.__doc__)
            )

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        others = [i for i in list(instance.context) if
                  i is not instance and
                  set(cls.families) & get_instance_families(i) and
                  instance.data["folderPath"] == i.data["folderPath"]]
        if not others:
            return []

        other_ids = defaultdict(list)
        for other in others:
            for _id, members in get_instance_node_ids(other).items():
                other_ids[_id].extend(members)

        # Take only the ids with more than one member
        invalid = list()
        ids = get_instance_node_ids(instance)
        for _id, members in ids.items():
            if _id in other_ids:

                members_str = ", ".join(members)
                others_str = "\n".join(
                    "- {}".format(other) for other in other_ids[_id]
                )

                cls.log.error(
                    "ID for node %s clashes with nodes from "
                    "other model instances:\n%s", members_str, others_str
                )
                invalid.extend(members)

        return invalid
