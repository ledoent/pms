# pylint: disable=print-used
import json
import os
from pathlib import Path

from odoo.api import Environment
from odoo.exceptions import UserError

env: Environment = globals()["env"]  # Provided by odoo shell.

company = env["res.company"].create({"name": "Consistency probe company"})
owner = env["res.partner"].create({"name": "Consistency probe owner"})
prop = env["pms.property"].create(
    {
        "name": "Consistency probe property",
        "owner_id": owner.id,
        "company_id": company.id,
        "min_nights": 1,
        "max_nights": 30,
        "tz": "UTC",
    }
)
accepted = False
error = None
try:
    with env.cr.savepoint():
        env["pms.reservation"].create(
            {
                "property_id": prop.id,
                "company_id": env.company.id,
                "start": "2032-01-01 12:00:00",
                "stop": "2032-01-03 12:00:00",
            }
        )
        accepted = True
except UserError as caught:
    error = str(caught)
Path(
    "/pms20-evidence/company-consistency-"
    + os.environ.get("PMS_COMPANY_PROBE_PHASE", "before")
    + ".json"
).write_text(
    json.dumps(
        {
            "mismatched_company_accepted": accepted,
            "error": error,
            "persistence": "rolled back",
        },
        indent=2,
    )
)
env.cr.rollback()
print(json.dumps({"mismatched_company_accepted": accepted, "error": error}))

if os.environ.get("PMS_COMPANY_PROBE_PHASE") == "after":
    assert not accepted, "Mismatched companies must be rejected"
