import re
from collections import defaultdict

import pyblish.api

from ayon_api import (
    get_products,
    get_last_versions
)
from ayon_core.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin,
    filter_instances_for_context_plugin
)


class ValidateSubsetsLastVersionTask(pyblish.api.InstancePlugin,
                                     OptionalPyblishPluginMixin):
    """Validate if current publish matches last version's task.

    If a particular subset (e.g. "pointcacheEnv") for an asset previously came
    from a different task this will raise an error to avoid accidentally
    overwriting publishes from another task.

    You can disable the validator if you are certain you want to publish
    into the existing subsets. Once you have published a new version then
    the new version's task matches your current task and thus the next time
    this will not invalidate.

    """

    order = pyblish.api.ValidatorOrder
    label = 'Match task last published version'
    hosts = ['maya']
    families = ["animation", "pointcache"]
    optional = True

    # Cache shared between all instances
    cache = None

    def process(self, instance):

        if not self.is_active(instance.data):
            return

        task = instance.data.get("task") or instance.context.data.get("task")
        last_task = self.get_last_task_for_instance(instance)
        if not last_task:
            self.log.debug("No last task found.")
            return

        self.log.debug("Last task: %s", last_task)
        if task == last_task:
            return

        product_name = instance.data["productName"]
        folder_path = instance.data["folderPath"]

        message = (
            "Last version of {} > {} was published "
            "from another task: {}. (current task: {})\n"
            "If you are sure this is what you want then you can disable "
            "the validator."
            "".format(folder_path, product_name, last_task, task)
        )
        raise PublishValidationError(
            title="Publish from different task",
            message=message,
            description=message
        )

    def populate_cache(self, context):
        """Populate cache to optimize the query for many instances

        On first run we cache this for all relevant instances in the context.
        """

        self.cache = {}

        # Confirm we are generating the product from the same task as before
        instances = list(
            filter_instances_for_context_plugin(plugin=self, context=context)
        )
        if not instances:
            return

        project_name = context.data["projectName"]

        # Get product names per asset id for the instances
        product_names_by_folder_id = defaultdict(set)
        for instance in instances:
            asset_id = instance.data["folderEntity"]["id"]
            product_name = instance.data["productName"]
            product_names_by_folder_id[asset_id].add(product_name)

        # Get the products
        products = list(get_products(
            project_name=project_name,
            names_by_folder_ids=product_names_by_folder_id,
            fields=["id", "name", "folderId"]
        ))
        if not products:
            return

        product_ids = {product["id"] for product in products}
        versions_by_product_id = get_last_versions(
            project_name=project_name,
            product_ids=product_ids,
            fields=["productId", "attrib.source"]
        )
        if not versions_by_product_id:
            return

        self.cache["version_by_asset_id_and_product_name"] = {
            (product["folderId"], product["name"]):
            versions_by_product_id.get(product["id"]) for product in products
        }

    def get_last_task_for_instance(self, instance):
        """Return task name of the last matching folder>product instance"""

        if self.cache is None:
            self.populate_cache(instance.context)

        if not self.cache:
            # No relevant data at all (no existing products or versions)
            return

        folder_id = instance.data["folderEntity"]["id"]
        product_name = instance.data["productName"]
        version = self.cache["version_by_asset_id_and_product_name"].get(
            (folder_id, product_name)
        )
        if version is None:
            self.log.debug("No existing version for {}".format(product_name))
            return

        # Since source task is not published along with the data we just
        # assume the task name from the root file path it was published from
        source = version.get("attrib", {}).get("source")
        if source is None:
            return

        # Assume workfile path matches /work/{task}/
        pattern = "/work/([^/]+)/"
        match = re.search(pattern, source)
        if match:
            return match.group(1)
