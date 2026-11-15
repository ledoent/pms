# Effective access and company boundaries

The migration converts the source ACL grants and global company rule to Odoo 20
`ir.access` definitions. New restrictions are isolated in the booking/access fix PRs.
Migration-only branches intentionally retain the original access behavior; the corrected
evaluation requires the companion fixes.

| Surface            | Migration behavior                                                                                          | Corrected evaluation                                                                                                                                                                                            |
| ------------------ | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Properties         | PMS users read; PMS managers CRUD; global rule permits shared properties or allowed companies               | Same internal grants and company boundary. Public/portal reads require publication; anonymous property create/write/delete grants are removed.                                                                  |
| Property contacts  | Source website overrides the core portal/public partner rule broadly                                        | Restores the own-commercial-partner domain. Adds read access only to published property partner records in allowed companies, preserving listing rendering without opening unrelated contacts.                  |
| Rooms and services | Source grants public read without a parent restriction; internal grants also lack a parent company boundary | Both public grants and global child rules require read access to the parent property. Regression cases cover unpublished parents and another company.                                                           |
| Reservations       | Source grants PMS users CRU and PMS managers CRUD without a company rule                                    | A global company domain restricts reservations to allowed companies/shared records. The property and sale-order links participate in Odoo’s automatic company consistency checks.                               |
| Reservation guests | Source internal grants are unrestricted by parent visibility                                                | Parent-reservation read access constrains guest records. Website inputs permit only name/email/phone and create new guests server-side. Forged partner/record/command fields are rejected.                      |
| Reservation types  | Source global/public rate reads                                                                             | Global types remain usable; property-specific types require an accessible parent. The booking route additionally requires a global rate or a rate belonging to the selected property and a reservation product. |
| Website booking    | Source sudo paths accept broad payloads                                                                     | Published property, current website/company, valid dates/night bounds, capacity, rate ownership and strict guest schema are checked before a savepoint creates reservation plus cart line.                      |

Evidence is in `evidence/regression-gates/`: the original public-access/HTTP
before-and-after runs, the isolated public child gate (both room and service subcases
fail before and pass after), and the internal child-company cases.
`evidence/company-consistency-before.json` records an accepted mismatched company;
`company-consistency-after.json` records rejection by the automatic company check. The
combined suite exercises the same restrictions with all eleven addons installed.

The source privilege policy that makes PMS managers website designers is preserved by
`pms_website_sale`. GoTime roles must not be mapped to that group without a later
explicit role-policy decision. No GoTime groups, record rules or guest accounts are
changed in this phase.

A model-level overlap search is not a concurrency exclusion. The ordinary sequential
checks use sudo only to avoid missing conflicting inventory hidden by record rules;
errors do not reveal the competing guest or record. Independent transactions can still
both pass before either commits. That remains an adoption blocker, documented in
`GOTIME-FIT.md` and `evidence/concurrency.json`.
