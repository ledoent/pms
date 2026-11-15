# Copyright (c) 2021 Gray Matter Logic
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import Command, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.pms_website.controllers.website import Website as PmsPropertyWebsite
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import WebsiteSale


class PropertyTableCompute:
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey, ppr):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= ppr:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(ppr):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=20, ppr=4):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(1, ppr)
            y = min(1, ppr)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % ppr, pos // ppr, x, y, ppr):
                pos += 1
            # if 21st product (index 20) and last line is full (ppr products), break
            # (pos + 1.0) / ppr is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // ppr) > maxy:
                break

            if x == 1 and y == 1:  # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {"product": p, "x": x, "y": y}
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows


class WebsiteSale(WebsiteSale):
    def _get_property_search_domain(self, search, category, guest, args):
        domain = [("is_published", "=", True)] + request.env.website.website_domain()
        domain.append(("company_id", "in", [False, request.env.website.company_id.id]))
        if search:
            domain += [("city", "ilike", search)]
        if guest:
            domain += [("no_of_guests", ">=", int(guest))]
        if category:
            domain += [("property_category_ids", "child_of", category.id)]
        if args.get("date_range"):
            date_range = args.get("date_range").split("-")
            start = date_range[0].strip() + " 00:00:00"
            end = date_range[1].strip() + " 23:59:59"
            start = datetime.strptime(start, "%m/%d/%Y %H:%M:%S")
            end = datetime.strptime(end, "%m/%d/%Y %H:%M:%S")
            Reservation = request.env["pms.reservation"].sudo()
            blocked = []
            for prop in request.env["pms.property"].search(domain):
                checkin, checkout = prop._get_stay_period(start.date(), end.date())
                if Reservation.search_count(
                    Reservation._get_overlap_domain(prop.id, checkin, checkout), limit=1
                ):
                    blocked.append(prop.id)
            domain += [("id", "not in", blocked)]
        domain += [("property_child_ids", "=", False)]
        return domain

    def _get_pricelist_context(self):
        pricelist_context = dict(request.env.context)
        pricelist = request.pricelist
        pricelist_context["pricelist"] = pricelist.id
        return pricelist_context, pricelist

    def _update_property_values(self, Property, post):
        values = {
            "city": list(
                {
                    property_rec.city
                    for property_rec in Property.search([])
                    if property_rec.city
                }
            )
        }
        return values

    @http.route(
        [
            """/property""",
            """/property/page/<int:page>""",
            """/property/category/<model("pms.website.category"):category>""",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def property(
        self, page=0, ppg=False, category=None, search="", guest_select="", **post
    ):
        Category = request.env["pms.website.category"]
        if category:
            category = Category.search([("id", "=", int(category))], limit=1)
        else:
            category = Category

        if ppg:
            try:
                ppg = int(ppg)
                post["ppg"] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env.website.shop_ppg or 20

        ppr = request.env.website.shop_ppr or 4

        domain = self._get_property_search_domain(
            search=search, category=category, guest=guest_select, args=post
        )

        keep = QueryURL("/property", category=category and int(category))

        pricelist_context, pricelist = self._get_pricelist_context()

        request.update_context(
            pricelist=pricelist.id, partner=request.env.user.partner_id
        )

        Property = request.env["pms.property"].with_context(bin_size=True)

        search_property = Property.search(domain, order="name asc")
        url = "/property"

        categs_domain = [("parent_id", "=", False)]
        if search:
            search_categories = Category.search(
                [("property_ids", "in", search_property.ids)]
            ).parents_and_self
            categs_domain.append(("id", "in", search_categories.ids))
        else:
            search_categories = Category
        categs = Category.search(categs_domain)

        if category:
            url = f"/shop/category/{request.env['ir.http']._slug(category)}"

        product_count = len(search_property)
        pager = request.env.website.pager(
            url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post
        )
        offset = pager["offset"]
        properties = search_property[offset : offset + ppg]

        layout_mode = "grid"

        values = self._update_property_values(Property=Property, post=post)
        # properties
        values.update(
            {
                "category": category,
                "search_city": search,
                "search_guest": guest_select,
                "search_raneg": post.get("date_range"),
                "pager": pager,
                "pricelist": pricelist,
                "properties": properties,
                "search_count": product_count,  # common for all searchbox
                "bins": PropertyTableCompute().process(properties, ppg, ppr),
                "ppg": ppg,
                "ppr": ppr,
                "keep": keep,
                "layout_mode": layout_mode,
                "categories": categs,
                "search_categories_ids": search_categories.ids,
            }
        )

        return request.render("pms_website_sale.properties", values)


class PmsWebsiteSale(PmsPropertyWebsite):
    def _prepare_property_values(self, pms_property, category, search, **kwargs):
        values = super()._prepare_property_values(
            pms_property, category, search, **kwargs
        )
        reservation_types = (
            request.env["pms.property.reservation"]
            .sudo()
            .search(
                [
                    "|",
                    ("property_id", "=", pms_property.id),
                    ("property_id", "=", False),
                ]
            )
        )
        values["reservation_types"] = reservation_types
        values["is_public_user"] = request.env.user._is_public()
        return values

    def _get_booking_property(self, property_id):
        return (
            request.env["pms.property"]
            .sudo()
            .search(
                [
                    ("id", "=", property_id),
                    ("is_published", "=", True),
                    ("website_id", "in", [False, request.env.website.id]),
                    ("company_id", "in", [False, request.env.website.company_id.id]),
                ],
                limit=1,
            )
        )

    def _get_booking_dates(self, prop, date_start, date_end):
        if not isinstance(date_start, str) or not isinstance(date_end, str):
            raise ValueError("Invalid dates")
        arrival = datetime.strptime(date_start, "%Y-%m-%d")
        departure = datetime.strptime(date_end, "%Y-%m-%d")
        nights = (departure - arrival).days
        if (
            nights <= 0
            or (prop.min_nights and nights < prop.min_nights)
            or (prop.max_nights and nights > prop.max_nights)
        ):
            raise ValueError("The stay does not meet the property's night limits")
        start, stop = prop._get_stay_period(arrival.date(), departure.date())
        return start, stop, nights

    @http.route(
        ["/property/<int:property_id>/check_availability"],
        type="jsonrpc",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def check_availability(self, property_id, date_start=None, date_end=None, **kwargs):
        prop = self._get_booking_property(property_id)
        if not prop:
            return {"available": False, "error": "Property not found"}
        if not date_start or not date_end:
            return {"available": False, "error": "Missing dates"}
        try:
            start, stop, _nights = self._get_booking_dates(prop, date_start, date_end)
        except (ValueError, TypeError):
            return {"available": False, "error": "Invalid dates"}
        Reservation = request.env["pms.reservation"].sudo()
        return {
            "available": not Reservation.search_count(
                Reservation._get_overlap_domain(prop.id, start, stop), limit=1
            )
        }

    @http.route(
        ["/property/<int:property_id>/add_to_cart"],
        type="jsonrpc",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def property_add_to_cart(
        self,
        property_id,
        date_start=None,
        date_end=None,
        reservation_type_id=None,
        guests=None,
        **kwargs,
    ):
        prop = self._get_booking_property(property_id)
        if not prop:
            return {"error": "Property not found", "redirect": "/property"}
        if request.env.user._is_public():
            return {
                "error": "Login required",
                "redirect": f"/web/login?redirect={prop.website_url}",
            }
        try:
            start, stop, nights = self._get_booking_dates(prop, date_start, date_end)
            if isinstance(reservation_type_id, bool) or not isinstance(
                reservation_type_id, (int, str)
            ):
                raise ValueError("Invalid reservation type")
            type_id = int(reservation_type_id)
        except (ValueError, TypeError):
            return {"error": "Invalid dates"}
        rate = (
            request.env["pms.property.reservation"]
            .sudo()
            .search(
                [
                    ("id", "=", type_id),
                    ("property_id", "in", [False, prop.id]),
                    ("product_id.reservation_ok", "=", True),
                ],
                limit=1,
            )
        )
        if not rate:
            return {"error": "Invalid reservation type"}
        if not isinstance(guests, list) or not 1 <= len(guests) <= prop.no_of_guests:
            return {"error": "The guest count exceeds this property's capacity"}
        clean_guests = []
        for guest in guests:
            if not isinstance(guest, dict) or set(guest) - {"name", "phone", "email"}:
                return {"error": "Invalid guest details"}
            if not isinstance(guest.get("name"), str) or not guest["name"].strip():
                return {"error": "At least one guest is required"}
            if any(
                not isinstance(value, str) or len(value) > 256
                for value in guest.values()
            ):
                return {"error": "Invalid guest details"}
            clean_guests.append({key: value.strip() for key, value in guest.items()})
        Reservation = request.env["pms.reservation"].sudo()
        if Reservation.search_count(
            Reservation._get_overlap_domain(prop.id, start, stop), limit=1
        ):
            return {"error": "Property is unavailable for these dates"}
        try:
            with request.env.cr.savepoint():
                reservation = Reservation.create(
                    {
                        "property_id": prop.id,
                        "reservation_type_id": rate.id,
                        "start": start,
                        "stop": stop,
                        "company_id": prop.company_id.id
                        or request.env.website.company_id.id,
                        "guest_ids": [Command.create(guest) for guest in clean_guests],
                        "partner_id": request.env.user.partner_id.id,
                    }
                )
                order = request.cart or request.env.website._create_cart()
                request.env["sale.order.line"].sudo().create(
                    {
                        "order_id": order.id,
                        "product_id": rate.product_id.id,
                        "product_uom_qty": nights,
                        "price_unit": rate.price,
                        "pms_reservation_id": reservation.id,
                    }
                )
        except ValidationError:
            return {"error": "The booking could not be created"}
        return {"redirect": "/shop/cart"}
