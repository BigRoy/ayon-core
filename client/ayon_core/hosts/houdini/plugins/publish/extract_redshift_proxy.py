import os

import pyblish.api

from ayon_core.pipeline import publish
from ayon_core.hosts.houdini.api.lib import render_rop

import hou


class ExtractRedshiftProxy(publish.Extractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Redshift Proxy"
    families = ["redshiftproxy"]
    hosts = ["houdini"]
    targets = ["local", "remote"]

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return
        ropnode = hou.node(instance.data.get("instance_node"))

        # Get the filename from the filename parameter
        # `.evalParm(parameter)` will make sure all tokens are resolved
        output = ropnode.evalParm("RS_archive_file")
        staging_dir = os.path.normpath(os.path.dirname(output))
        instance.data["stagingDir"] = staging_dir
        file_name = os.path.basename(output)

        self.log.info("Writing Redshift Proxy '%s' to '%s'" % (file_name,
                                                               staging_dir))

        render_rop(ropnode)

        output = instance.data["frames"]

        # Check if the user aborted the export process, since no error is
        # raised by Houdini if the user aborts it.
        user_aborted = False
        for warning in ropnode.warnings():
            self.log.warning(warning)
            if "extraction aborted by the user" in warning:
                user_aborted = True
        if user_aborted:
            raise RuntimeError("User aborted the extraction")

        # The extractor doesn't warn with user aborted message
        # if the user interrupted the process very early on - instead it
        # mentions some warnings related to OCIO. To ensure valid output
        # we'll perform a check expected output files exist
        missing_filenames = []
        for fname in output:
            path = os.path.join(staging_dir, fname)
            if not os.path.isfile(path):
                missing_filenames.append(fname)
        if missing_filenames:
            raise RuntimeError("Missing frames: {}".format(missing_filenames))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "rs",
            "ext": "rs",
            "files": output if len(output) > 1 else output[0],
            "stagingDir": staging_dir,
        }

        # A single frame may also be rendered without start/end frame.
        if "frameStartHandle" in instance.data and "frameEndHandle" in instance.data:  # noqa
            representation["frameStart"] = instance.data["frameStartHandle"]
            representation["frameEnd"] = instance.data["frameEndHandle"]

        instance.data["representations"].append(representation)
