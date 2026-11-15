# pylint: disable=print-used
import importlib.util
import json
from pathlib import Path

from odoo.api import Environment
from odoo.upgrade_code.material_symbols_icons_mapping import FA_TO_MATERIAL

env: Environment = globals()["env"]  # Provided by odoo shell.

room = env["pms.room.type"].create(
    {"name": "Legacy icon migration check", "icon": "fa-bed"}
)
unknown = env["pms.room.type"].create(
    {"name": "Unknown legacy icon migration check", "icon": "fa-unmapped-review-icon"}
)
module_path = (
    "/opt/odoo/custom/src/pms/pms_base/migrations/20.0.1.0.0/post-migration.py"
)
spec = importlib.util.spec_from_file_location("pms_icon_migration", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.migrate(env.cr, "19.0.1.0.0")
env.invalidate_all()
assert room.icon == FA_TO_MATERIAL["bed"][0]
assert unknown.icon == "check"
Path("/pms20-evidence/icon-migration.json").write_text(
    json.dumps(
        {
            "known_icon": room.icon,
            "fallback_icon": unknown.icon,
            "passed": True,
            "persistence": "rolled back synthetic probe",
        },
        indent=2,
    )
)
env.cr.rollback()
