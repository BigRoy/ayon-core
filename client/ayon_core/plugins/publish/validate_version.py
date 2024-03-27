import pyblish.api
from ayon_core.pipeline.publish import PublishValidationError


class ValidateVersion(pyblish.api.InstancePlugin):
    """Validate instance version.

    AYON does not allow overwriting previously published versions.
    """

    order = pyblish.api.ValidatorOrder

    label = "Validate Version"
    hosts = ["nuke", "maya", "houdini", "blender",
             "photoshop", "aftereffects"]

    optional = False
    active = True

    def process(self, instance):
        version = instance.data.get("version")
        latest_version = instance.data.get("latestVersion")

        if latest_version is not None and int(version) <= int(latest_version):
            # TODO: Remove full non-html version upon drop of old publisher
            msg = (
                "Version {0} from instance '{1}' that you are "
                "trying to publish is lower or equal to existing version: "
                "{2}.\n"
                "Please version up your workfile to a higher version number "
                "than {2}."
            ).format(version, instance.data["name"], latest_version)

            msg_markdown = (
                "## Higher version of publish already exists\n"
                "Version **{0}** from instance **{1}** that you are "
                "trying to publish is lower or equal to an existing version "
                "in the database. Version in database: **{2}**.\n\n"
                "Please version up your workfile to a higher version number "
                "than: **{2}**."
            ).format(version, instance.data["name"], latest_version)
            raise PublishValidationError(
                title="Higher version of publish already exists",
                message=msg,
                description=msg_markdown
            )