import pyblish.api

from ayon_core.pipeline import OpenPypePyblishPluginMixin
from ayon_core.lib import EnumDef
from ayon_core.modules.deadline.deadline_module import DeadlineModule


class CollectDeadlineMachineList(pyblish.api.InstancePlugin,
                                 OpenPypePyblishPluginMixin):

    label = "Collect Deadline Machine Limit"

    # Ordered just after Collect Pools so the attribute definitions show
    # after those
    order = pyblish.api.CollectorOrder + 0.425

    hosts = ["maya", "houdini", "fusion"]
    families = [
        # Maya
        "renderlayer",
        # Fusion
        "render",
        # Houdini
        "usdrender", "vray_rop", "karma_rop",
        "arnold_rop", "redshift_rop", "manta_rop"
    ]
    targets = ["local"]

    slaves = []

    @classmethod
    def apply_settings(cls, project_settings):
        # Colorbleed edit: Because we have only one Deadline URL we can
        #   always use the default and thus cache it to make the attribute def
        #   and enum
        deadline_url = next(iter(
            project_settings["deadline"]["deadline_urls"]
        ))["value"]
        cls.slaves = DeadlineModule.get_deadline_slaves_cached(
            deadline_url, log=cls.log
        )

    def process(self, instance):
        attr_values = self.get_attr_values_from_data(instance.data)

        # Store Whitelist or Blacklist in render globals
        render_globals = instance.data.setdefault("renderGlobals", dict())
        machine_list = attr_values.get("machineList", [])

        # Ignore potential empty values (e.g. the placeholder enum value)
        machine_list = [value for value in machine_list if value]

        if machine_list:
            machine_list = ",".join(sorted(machine_list))
            if attr_values.get("whitelist", True):
                machine_list_key = "Whitelist"
            else:
                machine_list_key = "Blacklist"

            self.log.debug("Setting Machine List as %s to: %s",
                           machine_list_key,
                           machine_list)

            render_globals[machine_list_key] = machine_list

    @classmethod
    def get_attribute_defs(cls):
        defs = super(CollectDeadlineMachineList, cls).get_attribute_defs()

        defs.extend([
            EnumDef("machineList",
                    label="Machine List",
                    default=None,
                    items=cls.slaves or [""],
                    hidden=not cls.slaves,
                    multiselection=True),
            EnumDef("whitelist",
                    label="Machine List (Allow/Deny)",
                    items={
                        True: "Allow List",
                        False: "Deny List",
                    },
                    hidden=not cls.slaves,
                    default=False),
        ])

        return defs
