# -*- coding: utf-8 -*-
"""Loader for Redshift proxy."""
import os
import clique

import maya.cmds as cmds

from ayon_core.settings import get_project_settings
from ayon_core.pipeline import load
from ayon_core.hosts.maya.api.lib import (
    namespaced,
    maintained_selection,
    unique_namespace,
    get_container_transforms,
    get_node_parent
)
from ayon_core.hosts.maya.api.pipeline import containerise
from ayon_core.hosts.maya.api.plugin import get_load_color_for_product_type


class RedshiftProxyLoader(load.LoaderPlugin):
    """Load Redshift proxy"""

    product_types = {"redshiftproxy"}
    representations = {"rs"}

    label = "Import Redshift Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        """Plugin entry point."""
        product_type = context["product"]["productType"]

        folder_name = context["folder"]["name"]
        namespace = namespace or unique_namespace(
            folder_name + "_",
            prefix="_" if folder_name[0].isdigit() else "",
            suffix="_",
        )

        # Ensure Redshift for Maya is loaded.
        cmds.loadPlugin("redshift4maya", quiet=True)

        path = self.filepath_from_context(context)
        with maintained_selection():
            cmds.namespace(addNamespace=namespace)
            with namespaced(namespace, new=False):
                nodes, group_node = self.create_rs_proxy(name, path)

        self[:] = nodes
        if not nodes:
            return

        # colour the group node
        project_name = context["project"]["name"]
        settings = get_project_settings(project_name)
        color = get_load_color_for_product_type(product_type, settings)
        if color is not None:
            red, green, blue = color
            cmds.setAttr("{0}.useOutlinerColor".format(group_node), 1)
            cmds.setAttr(
                "{0}.outlinerColor".format(group_node), red, green, blue
            )

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, context):

        node = container['objectName']
        assert cmds.objExists(node), "Missing container"

        members = cmds.sets(node, query=True) or []
        rs_meshes = cmds.ls(members, type="RedshiftProxyMesh")
        assert rs_meshes, "Cannot find RedshiftProxyMesh in container"
        repre_entity = context["representation"]
        filename = self.filepath_from_context(context)

        for rs_mesh in rs_meshes:
            cmds.setAttr("{}.fileName".format(rs_mesh),
                         filename,
                         type="string")

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     repre_entity["id"],
                     type="string")

    def remove(self, container):

        # Delete container and its contents
        if cmds.objExists(container['objectName']):
            members = cmds.sets(container['objectName'], query=True) or []
            cmds.delete([container['objectName']] + members)

        # Remove the namespace, if empty
        namespace = container['namespace']
        if cmds.namespace(exists=namespace):
            members = cmds.namespaceInfo(namespace, listNamespace=True)
            if not members:
                cmds.namespace(removeNamespace=namespace)
            else:
                self.log.warning("Namespace not deleted because it "
                                 "still has members: %s", namespace)

    def switch(self, container, context):
        if container["loader"] == self.__class__.__name__:
            self.update(container, context)
            return

        # We are switching from a different loader which likely does not
        # have a Redshift proxy node. So we will need to mimic whatever the
        # original container did. We just take the original parent and load
        # a new redshift proxy under it matching the transformations.
        self.log.info(
            "Switching from different loader: {}".format(
                container["loader"]
             )
        )
        root = get_container_transforms(container, root=True)
        self.log.info("Found existing root: {}".format(root))

        # The parent may be the parent group of the container so it might
        # get deleted with the removal of the original container. We
        # collect any data we might need to recreate it.
        parent = get_node_parent(root)
        parent_xform = None
        parent_parent = None
        parent_attrs = {}
        attrs = ["useOutlinerColor",
                 "outlinerColorR",
                 "outlinerColorG",
                 "outlinerColorB"]
        if parent:
            self.log.info("Found previous root parent: {}".format(parent))
            parent_xform = cmds.xform(parent,
                                      query=True,
                                      worldSpace=True,
                                      matrix=True)
            parent_parent = get_node_parent(parent)
            parent_attrs = {
                attr: cmds.getAttr("{}.{}".format(parent, attr))
                for attr in attrs
            }

        # Switching from another loader - we are likely best off just
        # mimicking any root transformations, removing the original
        # and loading a new representation
        load.remove_container(container)
        new_container = self.load(context,
                                  name=container["name"],
                                  namespace=container["namespace"])
        if parent:
            if not cmds.objExists(parent):
                self.log.info("Recreating parent: {}".format(parent))
                # Recreate the parent we want to parent to
                _, node_name = parent.rsplit("|", 1)
                parent = cmds.createNode("transform", name=node_name,
                                         parent=parent_parent)
                cmds.xform(parent, worldSpace=True, matrix=parent_xform)
                for attr, value in parent_attrs.items():
                    cmds.setAttr("{}.{}".format(parent, attr), value)

            new_root = get_container_transforms(new_container, root=True)
            cmds.parent(new_root, parent, relative=True)

    def create_rs_proxy(self, name, path):
        """Creates Redshift Proxies showing a proxy object.

        Args:
            name (str): Proxy name.
            path (str): Path to proxy file.

        Returns:
            (str, str): Name of mesh with Redshift proxy and its parent
                transform.

        """
        rs_mesh = cmds.createNode(
            'RedshiftProxyMesh', name="{}_RS".format(name))
        mesh_shape = cmds.createNode("mesh", name="{}_GEOShape".format(name))

        cmds.setAttr("{}.fileName".format(rs_mesh),
                     path,
                     type="string")

        cmds.connectAttr("{}.outMesh".format(rs_mesh),
                         "{}.inMesh".format(mesh_shape))

        # TODO: use the assigned shading group as shaders if existed
        # assign default shader to redshift proxy
        if cmds.ls("initialShadingGroup", type="shadingEngine"):
            cmds.sets(mesh_shape, forceElement="initialShadingGroup")

        group_node = cmds.group(empty=True, name="{}_GRP".format(name))
        mesh_transform = cmds.listRelatives(mesh_shape,
                                            parent=True, fullPath=True)
        cmds.parent(mesh_transform, group_node)
        nodes = [rs_mesh, mesh_shape, group_node]

        # determine if we need to enable animation support
        files_in_folder = os.listdir(os.path.dirname(path))
        collections, remainder = clique.assemble(files_in_folder)

        if collections:
            cmds.setAttr("{}.useFrameExtension".format(rs_mesh), 1)

        return nodes, group_node
