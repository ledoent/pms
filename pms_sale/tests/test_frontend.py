# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import HttpCase, tagged

from odoo.addons.web.tests.test_js import unit_test_error_checker


@tagged("post_install", "-at_install")
class TestPmsFrontend(HttpCase):
    def test_reservation_frontend(self):
        # The OCA module selection does not automatically select CrossModule
        # WebSuite tests. Run the PMS Hoot suite explicitly in addon CI.
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&id=d3546510",
            "",
            login="admin",
            timeout=600,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )
