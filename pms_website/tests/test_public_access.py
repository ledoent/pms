# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase, new_test_user


class TestPublishedPropertyAccess(TransactionCase):
    def test_public_access_is_read_only_and_published_only(self):
        owner = self.env["res.partner"].create({"name": "Access review owner"})
        properties = self.env["pms.property"].create(
            [
                {
                    "name": "Published access property",
                    "owner_id": owner.id,
                    "is_published": True,
                },
                {
                    "name": "Private access property",
                    "owner_id": owner.id,
                    "is_published": False,
                },
            ]
        )
        public = self.env.ref("base.public_user")
        visible = (
            self.env["pms.property"]
            .with_user(public)
            .search([("id", "in", properties.ids)])
        )
        self.assertEqual(visible, properties[:1])
        self.assertFalse(properties[:1].with_user(public).has_access("write"))
        self.assertFalse(
            self.env["pms.property"].with_user(public).has_access("create")
        )
        self.assertFalse(
            self.env["res.partner"]
            .with_user(public)
            .search([("id", "=", properties[1].partner_id.id)])
        )

    def test_public_child_records_follow_property_access(self):
        owner = self.env["res.partner"].create({"name": "Child access owner"})
        properties = self.env["pms.property"].create(
            [
                {
                    "name": "Published child property",
                    "owner_id": owner.id,
                    "is_published": True,
                },
                {
                    "name": "Private child property",
                    "owner_id": owner.id,
                    "is_published": False,
                },
            ]
        )
        product = self.env["product.product"].create(
            {"name": "Child service", "type": "service"}
        )
        public = self.env.ref("base.public_user")
        for model, values in [
            (
                "pms.room",
                {
                    "name": "Access room",
                    "type_id": self.env.ref("pms_base.pms_room_type_bed").id,
                },
            ),
            ("pms.service", {"name": product.id, "vendor_id": owner.id}),
        ]:
            with self.subTest(model=model):
                records = self.env[model].create(
                    [dict(values, property_id=prop.id) for prop in properties]
                )
                visible = (
                    self.env[model]
                    .with_user(public)
                    .search([("id", "in", records.ids)])
                )
                self.assertEqual(visible, records[:1])

    def test_internal_child_records_follow_property_companies(self):
        owner = self.env["res.partner"].create({"name": "Company child owner"})
        company = self.env["res.company"].create({"name": "Private child company"})
        properties = self.env["pms.property"].create(
            [
                {
                    "name": "Current company property",
                    "owner_id": owner.id,
                    "company_id": self.env.company.id,
                },
                {
                    "name": "Other company property",
                    "owner_id": owner.id,
                    "company_id": company.id,
                },
            ]
        )
        user = new_test_user(
            self.env,
            login="child-company-reader",
            groups="base.group_user,pms_base.group_pms_user",
            company_id=self.env.company.id,
        )
        product = self.env["product.product"].create(
            {"name": "Company child service", "type": "service"}
        )
        for model, values in [
            (
                "pms.room",
                {
                    "name": "Company access room",
                    "type_id": self.env.ref("pms_base.pms_room_type_bed").id,
                },
            ),
            ("pms.service", {"name": product.id, "vendor_id": owner.id}),
        ]:
            with self.subTest(model=model):
                records = self.env[model].create(
                    [dict(values, property_id=prop.id) for prop in properties]
                )
                visible = (
                    self.env[model].with_user(user).search([("id", "in", records.ids)])
                )
                self.assertEqual(visible, records[:1])
