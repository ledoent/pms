# Copyright (c) 2024 Gray Matter Logic
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
from datetime import datetime, timedelta

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPropertyBooking(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env.ref("pms_sale.product_product_reservation")
        cls.partner_owner = cls.env["res.partner"].create({"name": "Property Owner"})
        cls.property = cls.env["pms.property"].create(
            {
                "name": "Booking Test Property",
                "owner_id": cls.partner_owner.id,
                "no_of_guests": 4,
                "min_nights": 1,
                "tz": "UTC",
                "max_nights": 30,
                "website_published": True,
            }
        )
        cls.reservation_type = cls.env["pms.property.reservation"].create(
            {
                "name": "Standard Stay",
                "product_id": cls.product.id,
                "property_id": cls.property.id,
            }
        )
        today = datetime.now()
        # Use distinct date ranges per test to avoid cross-test interference
        cls.dates_free = (
            (today + timedelta(days=30)).strftime("%Y-%m-%d"),
            (today + timedelta(days=35)).strftime("%Y-%m-%d"),
        )
        cls.dates_conflict = (
            (today + timedelta(days=40)).strftime("%Y-%m-%d"),
            (today + timedelta(days=45)).strftime("%Y-%m-%d"),
        )
        cls.dates_cart = (
            (today + timedelta(days=50)).strftime("%Y-%m-%d"),
            (today + timedelta(days=55)).strftime("%Y-%m-%d"),
        )

    def _jsonrpc(self, url, params):
        return self.url_open(
            url,
            data=json.dumps(
                {"jsonrpc": "2.0", "method": "call", "params": params}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )

    def test_check_availability_available(self):
        """Property with no reservations reports available for given dates."""
        self.authenticate("admin", "admin")
        resp = self._jsonrpc(
            f"/property/{self.property.id}/check_availability",
            {"date_start": self.dates_free[0], "date_end": self.dates_free[1]},
        )
        result = resp.json()["result"]
        self.assertTrue(result["available"])

    def test_check_availability_conflict(self):
        """Property with a confirmed reservation reports unavailable for those dates."""
        stage_confirmed = self.env.ref(
            "pms_sale.pms_stage_confirmed", raise_if_not_found=False
        )
        self.env["pms.reservation"].create(
            {
                "name": "Existing Reservation",
                "property_id": self.property.id,
                "start": self.dates_conflict[0],
                "stop": self.dates_conflict[1],
                "stage_id": stage_confirmed.id,
            }
        )
        self.authenticate("admin", "admin")
        resp = self._jsonrpc(
            f"/property/{self.property.id}/check_availability",
            {
                "date_start": self.dates_conflict[0],
                "date_end": self.dates_conflict[1],
            },
        )
        result = resp.json()["result"]
        self.assertFalse(result["available"])

    def test_add_to_cart_creates_order_and_reservation(self):
        """Posting booking details creates a sale order line and linked reservation."""
        self.authenticate("admin", "admin")
        resp = self._jsonrpc(
            f"/property/{self.property.id}/add_to_cart",
            {
                "date_start": self.dates_cart[0],
                "date_end": self.dates_cart[1],
                "reservation_type_id": self.reservation_type.id,
                "guests": [
                    {
                        "name": "Alice",
                        "phone": "555-1234",
                        "email": "alice@test.com",
                    }
                ],
            },
        )
        result = resp.json()["result"]
        self.assertEqual(result.get("redirect"), "/shop/cart")
        reservation = self.env["pms.reservation"].search(
            [
                ("property_id", "=", self.property.id),
                ("start", "=", datetime.strptime(self.dates_cart[0], "%Y-%m-%d")),
            ],
            limit=1,
        )
        self.assertTrue(
            reservation,
            repr(
                self.env["pms.reservation"]
                .search([("property_id", "=", self.property.id)])
                .read(["start", "stop"])
            ),
        )
        self.assertTrue(reservation.sale_order_id)
        self.assertEqual(reservation.property_id, self.property)

    def test_add_to_cart_requires_login(self):
        """Public user attempting to add to cart receives a redirect to login."""
        self.authenticate(None, None)
        resp = self._jsonrpc(
            f"/property/{self.property.id}/add_to_cart",
            {
                "date_start": self.dates_cart[0],
                "date_end": self.dates_cart[1],
                "reservation_type_id": self.reservation_type.id,
                "guests": [{"name": "Bob"}],
            },
        )
        result = resp.json()["result"]
        self.assertIn("redirect", result)
        self.assertIn("/web/login", result["redirect"])

    def _payload(self, **values):
        return {
            "date_start": self.dates_cart[0],
            "date_end": self.dates_cart[1],
            "reservation_type_id": self.reservation_type.id,
            "guests": [{"name": "Review guest"}],
            **values,
        }

    def _book(self, **values):
        self.authenticate("admin", "admin")
        data = self._jsonrpc(
            f"/property/{self.property.id}/add_to_cart", self._payload(**values)
        ).json()
        self.assertIn("result", data, data)
        return data["result"]

    def test_forged_guest_fields_are_rejected_without_side_effects(self):
        before = self.env["pms.reservation"].search_count([])
        result = self._book(
            guests=[{"name": "Forged guest", "partner_id": self.partner_owner.id}]
        )
        self.assertIn("error", result)
        self.assertEqual(self.env["pms.reservation"].search_count([]), before)

    def test_unrelated_reservation_type_is_rejected(self):
        other = self.property.copy({"name": "Unrelated property"})
        rate = self.reservation_type.copy({"property_id": other.id})
        self.assertIn("error", self._book(reservation_type_id=rate.id))

    def test_reversed_dates_are_rejected(self):
        self.assertIn(
            "error",
            self._book(date_start=self.dates_cart[1], date_end=self.dates_cart[0]),
        )

    def test_malformed_guest_input_returns_validation_error(self):
        self.assertIn("error", self._book(guests=["forged"]))

    def test_excess_capacity_is_rejected(self):
        self.assertIn(
            "error", self._book(guests=[{"name": f"Guest {i}"} for i in range(5)])
        )

    def test_unpublished_property_is_not_available(self):
        self.property.is_published = False
        self.authenticate(None, None)
        result = self._jsonrpc(
            f"/property/{self.property.id}/check_availability", self._payload()
        ).json()["result"]
        self.assertFalse(result["available"])
        self.assertIn("error", result)

    def test_confirmed_overlap_cannot_be_added_to_cart(self):
        self.env["pms.reservation"].create(
            {
                "property_id": self.property.id,
                "start": self.dates_cart[0],
                "stop": self.dates_cart[1],
                "stage_id": self.env.ref("pms_sale.pms_stage_confirmed").id,
            }
        )
        self.assertIn("error", self._book())

    def test_back_to_back_availability(self):
        self.env["pms.reservation"].create(
            {
                "property_id": self.property.id,
                "start": (
                    datetime.strptime(self.dates_cart[0], "%Y-%m-%d")
                    - timedelta(days=2)
                ),
                "stop": self.dates_cart[0],
                "stage_id": self.env.ref("pms_sale.pms_stage_confirmed").id,
            }
        )
        self.authenticate(None, None)
        result = self._jsonrpc(
            f"/property/{self.property.id}/check_availability", self._payload()
        ).json()["result"]
        self.assertTrue(result["available"])

    def test_booking_uses_property_timezone_and_rate(self):
        self.property.write({"tz": "America/New_York", "checkin": 15, "checkout": 11})
        self.assertEqual(
            self._book(date_start="2030-03-09", date_end="2030-03-11").get("redirect"),
            "/shop/cart",
        )
        reservation = self.env["pms.reservation"].search(
            [("property_id", "=", self.property.id)], order="id desc", limit=1
        )
        self.assertEqual(reservation.start, datetime(2030, 3, 9, 20))
        self.assertEqual(reservation.stop, datetime(2030, 3, 11, 15))
        self.assertEqual(reservation.duration, 2)
        self.assertEqual(reservation.reservation_type_id, self.reservation_type)
