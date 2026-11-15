# pylint: disable=print-used
# Run via Odoo shell against pms20_ui, with test_enable=False.
import concurrent.futures
import json
import threading
from pathlib import Path

from odoo import api
from odoo.api import Environment

env: Environment = globals()["env"]  # Provided by odoo shell.

owner = env["res.partner"].create({"name": "Concurrent booking probe owner"})
prop = env["pms.property"].create(
    {
        "name": "Concurrent booking probe property",
        "owner_id": owner.id,
        "company_id": env.company.id,
        "tz": "UTC",
        "min_nights": 1,
        "max_nights": 30,
    }
)
stage_id = env.ref("pms_sale.pms_stage_confirmed").id
property_id = prop.id
registry = env.registry
company_id = env.company.id
env.cr.commit()
barrier = threading.Barrier(2)


def reserve(index):
    try:
        with registry.cursor() as cursor:
            isolated = api.Environment(cursor, 1, {"allowed_company_ids": [company_id]})
            barrier.wait(timeout=30)
            reservation = isolated["pms.reservation"].create(
                {
                    "property_id": property_id,
                    "company_id": company_id,
                    "stage_id": stage_id,
                    "start": "2031-02-01 15:00:00",
                    "stop": "2031-02-04 11:00:00",
                }
            )
            # Both constraints have run before either transaction commits.
            barrier.wait(timeout=30)
            cursor.commit()
            return {"worker": index, "committed": True, "id": reservation.id}
    except Exception as error:
        return {"worker": index, "committed": False, "error": repr(error)}


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(reserve, (1, 2)))
with registry.cursor() as cursor:
    isolated = api.Environment(cursor, 1, {})
    count = isolated["pms.reservation"].search_count(
        [("property_id", "=", property_id), ("stage_id", "=", stage_id)]
    )
data = {
    "test_enable": False,
    "independent_transactions": True,
    "property_id": property_id,
    "results": results,
    "confirmed_stays_same_interval": count,
    "adoption_blocker": count > 1,
}
Path("/pms20-evidence/concurrency.json").write_text(json.dumps(data, indent=2))
print(json.dumps(data))
