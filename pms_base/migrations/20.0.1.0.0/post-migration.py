# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tools import SQL
from odoo.upgrade_code.material_symbols_icons_mapping import FA_TO_MATERIAL


def migrate(cr, version):
    for table in ("pms_service", "pms_room_type"):
        cr.execute(
            SQL(
                "SELECT DISTINCT icon FROM %s WHERE icon LIKE %s",
                SQL.identifier(table),
                "fa-%",
            )
        )
        for (old,) in cr.fetchall():
            new = FA_TO_MATERIAL.get(old[3:], ("check", False))[0]
            cr.execute(
                SQL(
                    "UPDATE %s SET icon = %s WHERE icon = %s",
                    SQL.identifier(table),
                    new,
                    old,
                )
            )
