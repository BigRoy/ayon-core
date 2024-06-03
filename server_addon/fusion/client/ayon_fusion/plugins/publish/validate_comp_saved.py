import os

import pyblish.api
from ayon_core.pipeline import PublishValidationError


class ValidateFusionCompSaved(pyblish.api.ContextPlugin):
    """Ensure current comp is saved"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Comp Saved"
    families = ["render", "image"]
    hosts = ["fusion"]

    def process(self, context):

        comp = context.data.get("currentComp")
        assert comp, "Must have Comp object"
        attrs = comp.GetAttrs()

        filename = attrs["COMPS_FileName"]
        if not filename:
            raise PublishValidationError("Comp is not saved.",
                                         title=self.label)

        if not os.path.exists(filename):
            raise PublishValidationError(
                "Comp file does not exist: %s" % filename, title=self.label)

        if attrs["COMPB_Modified"]:
            # This is a debug log since the publishing itself will save the
            # current comp file anyway; as such the warning is technically
            # redundant
            self.log.debug("Comp is modified. Save your comp to ensure your "
                           "changes propagate correctly if you get unexpected "
                           "results.")
