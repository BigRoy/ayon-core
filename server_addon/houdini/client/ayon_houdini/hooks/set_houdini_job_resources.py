import os
from ayon_core.lib import PreLaunchHook


def add_path_to_env(env, key, path):
    existing = env.get(key)
    if existing:
        env[key] = os.pathsep.join([existing, path])
    else:
        env[key] = path


class HoudiniSetJobResourcesEnvs(PreLaunchHook):
    """Set project environment variables for Houdini.

    - Set `{project}/resources` to `JOB`.
    - Add `{project}/resources/otls` to `HOUDINI_OTLSCAN_PATH`
    - Add `{project}/resources/scripts/houdinipath` to `PYTHONPATH`

    Hook `GlobalHostDataHook` must be executed before this hook.

    """
    app_groups = ["houdini"]

    def execute(self):

        work_root = str(self.data["anatomy"].roots["work"])
        project_name = self.data["project_name"]

        project_root_work = os.path.join(work_root, project_name)
        project_resources = os.path.join(project_root_work, "resources")
        project_resource_otls = os.path.join(project_resources, "otls")
        project_resources_pythonpath = os.path.join(project_resources,
                                                    "scripts",
                                                    "houdinipath")

        self.log.info("Setting JOB and HOUDINI_OTLSCAN_PATH.")
        self.launch_context.env.update({
            "JOB": project_resources,
            "HOUDINI_OTLSCAN_PATH": f"{project_resource_otls};&"
        })

        add_path_to_env(env=self.launch_context.env,
                        key="PYTHONPATH",
                        path=project_resources_pythonpath)
