# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestBookingBoundaries(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = cls.env["res.partner"].create({"name": "Boundary owner"})
        cls.property = cls.env["pms.property"].create(
            {
                "name": "Boundary property",
                "owner_id": cls.owner.id,
                "company_id": cls.env.company.id,
                "no_of_guests": 4,
                "min_nights": 1,
                "max_nights": 30,
                "tz": "America/New_York",
            }
        )

    def _stay(self, start="2030-01-01 12:00:00", stop="2030-01-03 12:00:00", **values):
        return self.env["pms.reservation"].create(
            {
                "property_id": self.property.id,
                "start": start,
                "stop": stop,
                "stage_id": self.env.ref("pms_sale.pms_stage_confirmed").id,
                **values,
            }
        )

    def test_back_to_back_stays_are_allowed(self):
        self._stay()
        self._stay("2030-01-03 12:00:00", "2030-01-05 12:00:00")

    def test_property_filter_uses_checkout_boundaries(self):
        self.property.write({"tz": "UTC", "checkin": 12, "checkout": 12})
        self._stay()
        result = self.env["pms.property"].get_property_information(
            {"datepicker_value": "01/03/2030 - 01/05/2030"}
        )
        self.assertIn(self.property.id, [record["id"] for record in result])

    def test_property_filter_ignores_cancelled_stays(self):
        self.property.write({"tz": "UTC", "checkin": 12, "checkout": 12})
        self._stay(stage_id=self.env.ref("pms_sale.pms_stage_cancelled").id)
        result = self.env["pms.property"].get_property_information(
            {"datepicker_value": "01/01/2030 - 01/03/2030"}
        )
        self.assertIn(self.property.id, [record["id"] for record in result])

    def test_actual_overlap_is_rejected(self):
        self._stay()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._stay("2030-01-02 12:00:00", "2030-01-05 12:00:00")

    def test_cancelled_and_draft_stays_do_not_block(self):
        self._stay(stage_id=self.env.ref("pms_sale.pms_stage_cancelled").id)
        self._stay(stage_id=self.env.ref("pms_sale.pms_stage_new").id)
        self._stay()

    def test_reversed_dates_are_rejected(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._stay("2030-01-03 12:00:00", "2030-01-01 12:00:00")

    def test_short_overnight_is_one_calendar_night(self):
        stay = self._stay("2030-01-02 01:00:00", "2030-01-02 11:00:00")
        self.assertEqual(stay.duration, 1)

    def test_dst_spring_and_autumn_stays_each_have_one_night(self):
        for start, stop in [
            ("2030-03-09 20:00:00", "2030-03-10 19:00:00"),
            ("2030-11-02 19:00:00", "2030-11-03 20:00:00"),
        ]:
            self.assertEqual(self._stay(start, stop).duration, 1)

    def test_guest_count_is_computed_per_reservation(self):
        stays = self.env["pms.reservation"].create(
            [
                {
                    "property_id": self.property.id,
                    "start": "2030-01-01",
                    "stop": "2030-01-03",
                    "guest_ids": [
                        Command.create({"name": f"Guest {index}-{guest}"})
                        for guest in range(index)
                    ],
                }
                for index in (1, 2)
            ]
        )
        self.assertEqual(stays.mapped("no_of_guests"), [1, 2])

    def test_stay_bounds_are_inclusive_and_maximum_is_enforced(self):
        self.property.write({"min_nights": 2, "max_nights": 3})
        self._stay()
        self._stay("2030-02-01 12:00:00", "2030-02-04 12:00:00")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._stay("2030-03-01 12:00:00", "2030-03-05 12:00:00")

    def test_capacity_is_enforced(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._stay(
                guest_ids=[Command.create({"name": f"Guest {i}"}) for i in range(5)]
            )

    def test_reservations_are_isolated_by_company(self):
        company = self.env["res.company"].create({"name": "Other reservation company"})
        prop = self.env["pms.property"].create(
            {
                "name": "Other company property",
                "owner_id": self.owner.id,
                "company_id": company.id,
                "min_nights": 1,
                "max_nights": 30,
            }
        )
        other = self._stay(property_id=prop.id, company_id=company.id)
        user = new_test_user(
            self.env,
            login="boundary-company-user",
            groups="base.group_user,pms_base.group_pms_manager",
            company_id=self.env.company.id,
        )
        self.assertFalse(
            self.env["pms.reservation"].with_user(user).search([("id", "=", other.id)])
        )

    def test_property_and_reservation_companies_must_match(self):
        company = self.env["res.company"].create({"name": "Consistency company"})
        prop = self.env["pms.property"].create(
            {
                "name": "Consistency property",
                "owner_id": self.owner.id,
                "company_id": company.id,
                "min_nights": 1,
                "max_nights": 30,
            }
        )
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._stay(property_id=prop.id, company_id=self.env.company.id)
