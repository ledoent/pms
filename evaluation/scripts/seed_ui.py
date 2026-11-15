# pylint: disable=print-used
# Executed by odoo shell against the dedicated synthetic UI database.
import json
from datetime import timedelta
from pathlib import Path

from odoo import Command, fields
from odoo.api import Environment

env: Environment = globals()["env"]  # Provided by odoo shell.

owner = env["res.partner"].create(
    {"name": "PMS Review Owner", "email": "owner@example.invalid"}
)
guest = env["res.partner"].create(
    {"name": "PMS Review Guest", "email": "guest@example.invalid"}
)
prop = env["pms.property"].create(
    {
        "name": "PMS Review Property",
        "owner_id": owner.id,
        "company_id": env.company.id,
        "tz": "America/New_York",
        "city": "Boston",
        "no_of_guests": 4,
        "min_nights": 1,
        "max_nights": 30,
        "checkin": 15,
        "checkout": 11,
        "is_published": True,
        "website_id": env.ref("base.default_website").id,
    }
)
env["pms.room"].create(
    {
        "name": "Review bedroom",
        "property_id": prop.id,
        "type_id": env.ref("pms_base.pms_room_type_bed").id,
    }
)
rate = env["pms.property.reservation"].create(
    {"name": "Review nightly rate", "property_id": prop.id, "price": 120}
)
product = rate.product_id
product.invoice_policy = "order"
account = env["account.account"].search(
    [("account_type", "=", "income"), ("company_ids", "in", env.company.id)], limit=1
)
if account:
    product.property_account_income_id = account
today = fields.Date.today()
stay = env["pms.reservation"].create(
    {
        "property_id": prop.id,
        "partner_id": guest.id,
        "reservation_type_id": rate.id,
        "start": today + timedelta(days=7),
        "stop": today + timedelta(days=10),
        "guest_ids": [
            Command.create(
                {"name": "Synthetic guest", "email": "guest@example.invalid"}
            )
        ],
    }
)
order = env["sale.order"].create({"partner_id": guest.id})
env["sale.order.line"].create(
    {
        "order_id": order.id,
        "product_id": product.id,
        "product_uom_qty": stay.duration,
        "price_unit": rate.price,
        "pms_reservation_id": stay.id,
    }
)
env.company.iap_enrich_auto_done = True
actions = {}
for key, xmlid in {
    "properties": "pms_base.action_pms_property",
    "reservations": "pms_sale.action_pms_reservation",
    "timeline": "pms_sale.action_sale_reservation",
    "configurator": "pms_sale.pms_configurator_action",
    "sales": "sale.action_orders",
    "projects": "project.open_view_project_all",
}.items():
    record = env.ref(xmlid, raise_if_not_found=False)
    if record:
        actions[key] = record.id
data = {
    "owner": owner.id,
    "guest": guest.id,
    "property": prop.id,
    "rate": rate.id,
    "product": product.id,
    "reservation": stay.id,
    "order": order.id,
    "property_url": prop.website_url,
    "actions": actions,
}
Path("/pms20-evidence/ui/seed.json").write_text(json.dumps(data, indent=2))
env.cr.commit()
print(json.dumps(data))
