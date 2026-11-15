// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import {expect, test} from "@odoo/hoot";
import {defineMailModels} from "@mail/../tests/mail_test_helpers";
import {animationFrame} from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    preloadBundle,
} from "@web/../tests/web_test_helpers";

class Property extends models.Model {
    _name = "pms.property";
    name = fields.Char();
    _records = [
        {id: 1, name: "Boston unit"},
        {id: 2, name: "Denver unit"},
    ];
}

class Reservation extends models.Model {
    _name = "pms.reservation";
    name = fields.Char();
    start = fields.Date();
    stop = fields.Date();
    property_id = fields.Many2one({relation: "pms.property"});
    _records = [
        {
            id: 1,
            name: "Boston stay",
            start: "2019-03-10",
            stop: "2019-03-12",
            property_id: 1,
        },
        {
            id: 2,
            name: "Denver stay",
            start: "2019-03-11",
            stop: "2019-03-13",
            property_id: 2,
        },
    ];
}

defineMailModels();
defineModels([Property, Reservation]);
preloadBundle("web_timeline.vis-timeline_lib");
onRpc("has_access", () => true);
onRpc("get_selections", () => ({city: ["Boston", "Denver"]}));

test("PMS timeline filters and restores the loaded reservations", async () => {
    onRpc("get_property_information", ({args}) => {
        expect(args[0].city_value).toBe("Boston");
        return [{id: 1, name: "Boston unit"}];
    });
    await mountView({
        type: "timeline",
        resModel: "pms.reservation",
        arch: '<timeline date_start="start" date_stop="stop" default_group_by="property_id"/>',
    });
    await animationFrame();
    expect(".vis-item").toHaveCount(2);
    expect(".pms-city-select option").toHaveCount(3);
    await contains(".pms-city-select").select("Boston");
    await contains(".pms-timeline-filters button").click();
    await animationFrame();
    expect(".vis-item").toHaveCount(1);
    await contains(".pms-city-select").select("");
    await contains(".pms-timeline-filters button").click();
    await animationFrame();
    expect(".vis-item").toHaveCount(2);
});
