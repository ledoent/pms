# pylint: disable=print-used
# Odoo shell, synthetic evaluation DB only. Fail on missing links or outputs.
import json
from pathlib import Path

from odoo import Command
from odoo.api import Environment

env: Environment = globals()["env"]  # Provided by odoo shell.

prop = env["pms.property"].browse(157)
assert prop.exists()
partner = env["res.partner"].create(
    {"name": "Supporting flow vendor", "email": "vendor@example.invalid"}
)
product = env["product.product"].create(
    {"name": "Property maintenance service", "type": "service", "list_price": 125}
)
contract = env["contract.contract"].create(
    {
        "name": "Review monthly maintenance",
        "partner_id": partner.id,
        "contract_type": "purchase",
        "contract_line_ids": [
            Command.create(
                {
                    "name": "Monthly property maintenance",
                    "product_id": product.id,
                    "quantity": 1,
                    "price_unit": 125,
                    "date_start": "2026-11-01",
                    "recurring_next_date": "2026-11-01",
                    "recurring_rule_type": "monthly",
                    "property_id": prop.id,
                }
            )
        ],
    }
)
service = env["pms.service"].create(
    {
        "name": product.id,
        "property_id": prop.id,
        "vendor_id": partner.id,
        "contract_id": contract.id,
    }
)
invoices = contract.recurring_create_invoice()
assert invoices and prop.id in invoices.invoice_line_ids.mapped("property_ids").ids
assert contract in prop.contract_ids
accounts = {}
for key, code, kind in [
    ("asset", "REV100", "asset_fixed"),
    ("depreciation", "REV110", "asset_fixed"),
    ("expense", "REV600", "expense_depreciation"),
]:
    accounts[key] = env["account.account"].create(
        {"name": "Review " + key, "code": code, "account_type": kind}
    )
journal = env["account.journal"].create(
    {"name": "Review depreciation", "code": "REVD", "type": "general"}
)
profile = env["account.asset.profile"].create(
    {
        "name": "Review equipment profile",
        "account_asset_id": accounts["asset"].id,
        "account_depreciation_id": accounts["depreciation"].id,
        "account_expense_depreciation_id": accounts["expense"].id,
        "journal_id": journal.id,
    }
)
asset = env["account.asset"].create(
    {
        "name": "Review property equipment",
        "profile_id": profile.id,
        "purchase_value": 1200,
        "date_start": "2026-11-01",
        "property_id": prop.id,
    }
)
asset.compute_depreciation_board()
assert asset.depreciation_line_ids, "Depreciation board must contain real lines"
assert asset in prop.asset_ids
project = env["project.project"].create({"name": "Property maintenance review"})
task = env["project.task"].create(
    {
        "name": "Repair review property equipment",
        "project_id": project.id,
        "pms_property_ids": [Command.set(prop.ids)],
    }
)
assert prop in task.pms_property_ids
lead = env["crm.lead"].create(
    {"name": "Property review inquiry", "property_ids": [Command.set(prop.ids)]}
)
stock_product = env["product.product"].create(
    {
        "name": "Review property inventory",
        "type": "consu",
        "is_storable": True,
        "purchase_ok": True,
    }
)
order = env["purchase.order"].create(
    {
        "partner_id": partner.id,
        "order_line": [
            Command.create(
                {
                    "product_id": stock_product.id,
                    "product_qty": 2,
                    "price_unit": 25,
                    "pms_property_id": prop.id,
                }
            )
        ],
    }
)
order.order_line._onchange_pms_property_id()
order.button_confirm()
assert order.state == "purchase"
assert order.order_line.pms_property_id == prop
assert prop.stock_location_id and prop.stock_location_id.company_id == prop.company_id
moves = order.picking_ids.move_ids
assert moves, "Confirmed purchase must generate stock moves"
output = {
    "property": prop.id,
    "contract": contract.id,
    "contract_invoice_ids": invoices.ids,
    "asset": asset.id,
    "depreciation_lines": len(asset.depreciation_line_ids),
    "project": project.id,
    "task": task.id,
    "lead": lead.id,
    "purchase": order.id,
    "purchase_state": order.state,
    "stock_location": prop.stock_location_id.id,
    "stock_moves": moves.ids,
    "invoice_property_link": True,
    "asset_property_link": True,
    "task_property_link": True,
    "purchase_property_link": True,
}
Path("/pms20-evidence/supporting-flows.json").write_text(json.dumps(output, indent=2))
env.cr.commit()
print(json.dumps(output))
