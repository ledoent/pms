# Copyright (c) 2021 Gray Matter Logic
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmsProperty(models.Model):
    _inherit = "pms.property"

    checkin = fields.Float()
    checkout = fields.Float()
    reservation_ids = fields.One2many(
        "pms.property.reservation", "property_id", string="Reservation Types"
    )
    pms_mail_ids = fields.One2many("pms.mail", "property_id", string="Communication")
    no_of_guests = fields.Integer("Number of Guests")
    min_nights = fields.Integer("Minimum Nights")
    max_nights = fields.Integer("Maximum Nights")
    listing_type = fields.Selection(
        selection=[
            ("private_room", "Private Room"),
            ("entire_home", "Entire Home"),
            ("shared_room", "Shared Room"),
        ],
    )

    @api.model
    def get_property_information(self, vals, domain=False):
        domain = domain or []
        domain.append(("property_child_ids", "=", False))
        if vals.get("city_value") and vals.get("city_value") != "Select City":
            domain += [("city", "=", vals.get("city_value"))]
        if vals.get("bedrooms_value") and vals.get("bedrooms_value") != 0:
            domain += [("qty_bedroom", ">=", vals.get("bedrooms_value"))]
        if vals.get("datepicker_value"):
            try:
                date_range = vals["datepicker_value"].split("-")
                arrival = datetime.strptime(date_range[0].strip(), "%m/%d/%Y").date()
                departure = datetime.strptime(date_range[1].strip(), "%m/%d/%Y").date()
                if departure <= arrival:
                    raise ValueError("Invalid stay")
            except (ValueError, IndexError, AttributeError) as error:
                raise ValidationError(
                    self.env._("Use a valid checkin and checkout date range.")
                ) from error
            Reservation = self.env["pms.reservation"].sudo()
            blocked = []
            for prop in self.search(domain):
                start, stop = prop._get_stay_period(arrival, departure)
                if Reservation.search_count(
                    Reservation._get_overlap_domain(prop.id, start, stop), limit=1
                ):
                    blocked.append(prop.id)
            domain.append(("id", "not in", blocked))
        return self.search_read(domain, ["ref", "name"])

    def _get_stay_period(self, arrival, departure):
        self.ensure_one()
        timezone = ZoneInfo(self.tz or "UTC")
        start = datetime.combine(arrival, datetime.min.time()) + timedelta(
            hours=self.checkin
        )
        stop = datetime.combine(departure, datetime.min.time()) + timedelta(
            hours=self.checkout
        )
        return tuple(
            value.replace(tzinfo=timezone, fold=1).astimezone(UTC).replace(tzinfo=None)
            for value in (start, stop)
        )
