/** @odoo-module **/
// Copyright (c) 2021 Gray Matter Logic
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import {onWillStart, proxy} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {TimelineRenderer} from "@web_timeline/views/timeline/timeline_renderer.esm";

patch(TimelineRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.params.resModel === "pms.reservation") {
            this.pmsFilter = proxy({
                city: "",
                datepicker: "",
                bedrooms: "",
                cities: [],
            });
            this.pmsFilterRequest = 0;
            onWillStart(async () => {
                const selections = await this.orm.call(
                    "pms.reservation",
                    "get_selections",
                    []
                );
                this.pmsFilter.cities = selections.city || [];
            });
        }
    },

    _onPmsFilterSearch() {
        return this.on_data_loaded(this.model.data, false);
    },

    async on_data_loaded(records, adjust_window) {
        if (this.pmsFilter) {
            const request = ++this.pmsFilterRequest;
            const {city, datepicker, bedrooms} = this.pmsFilter;
            if (city || datepicker || bedrooms) {
                const properties = await this.orm.call(
                    "pms.property",
                    "get_property_information",
                    [
                        {
                            city_value: city || false,
                            datepicker_value: datepicker || false,
                            bedrooms_value: bedrooms || false,
                        },
                    ]
                );
                if (request !== this.pmsFilterRequest) {
                    return;
                }
                const propertyIds = new Set(properties.map((property) => property.id));
                records = records.filter((record) =>
                    propertyIds.has(record.property_id?.[0])
                );
            }
        }
        return super.on_data_loaded(records, adjust_window);
    },
});
