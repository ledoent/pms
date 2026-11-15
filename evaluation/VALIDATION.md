# Validation of the locked PMS evaluation

All 15 draft fork candidates pass pre-commit and their Odoo/OCB jobs at the exact heads in `evidence/ci-current.json`. The unreleased-dependency check passes for `pms_base` and remains red for the other candidates because they intentionally pin unmerged dependencies. This is separate from functional failures. The combined evaluation branch also passes repository-wide pre-commit (`evidence/aggregate-precommit-final-pass.log`).

The final combined fresh installation of all eleven PMS addons ran **233 tests, zero failures and zero errors** (`evidence/combined-final2.log`). Each individual review installed into a fresh database and ran nonzero tests: base 60, account 27, sale 19, project 1, CRM 7, stock 10, purchase 3, contract 13, assets 8, website 39, website sale 20, minimum nights 22, booking boundaries 35, website access 42, website booking 29. These are runner summary counts, not sums of per-module internal statistics. Each bundle includes its exact candidate SHA, raw test output and coverage JSON.

The isolated services are `odoo-prod-20` and `db-prod-20`, on port 19320 and dedicated synthetic databases/volumes. Both images, every external addon source, the published timeline wheel and all candidate heads are pinned in `evaluation-lock.json`. `evidence/wheel-integrity.json` confirms the assembled timeline sources match the wheel. The generic review UI/regression helpers assume older services; the recorded task-local adapters use these Odoo 20 services, `--with-demo`, exact DB filters and clean core templates. No GoTime stack was modified.

## Workflow evidence

Completed native browser captures (JSON records the explicit actions, browser errors and lock hash):

| Workflow | Evidence under `evidence/ui/` |
| --- | --- |
| Create a property | `property-created.json` / PNG |
| Configure a reservation and save the guest | `configurator-saved.json` / PNG |
| Filter the timeline by city and restore all cities | `timeline-final.json`, `04-timeline-Boston.png` |
| Confirm a sales order | `sale-confirmed.json` / PNG |
| Create and view its draft invoice | `invoice-visible.json` / PNG |
| Book and confirm a reservation | `reservation-confirmation-complete.json` / PNG |
| Explicitly cancel a confirmed reservation | `reservation-cancellation-complete.json` / PNG |
| Add two separate three-night website stays to a cart | `website-cart-final.json` / PNG |
| Timeline frontend unit test | `hoot-calendar-fixture.json` and `hoot-mobile-verified.json`: one test, five assertions each |

The final captures have no recorded browser errors. Supporting contract invoicing, asset depreciation, task/property links, CRM and confirmed purchase/stock links were exercised through ORM/API (`evidence/supporting-flows.json`), rather than through UI creation. The website check stops at the cart; it does not take a real payment. Mobile Hoot verifies frontend behavior; actual narrow viewport business layouts, resized-input appearance and keyboard focus remain unverified. Per-candidate frontend critiques state their evidence scope.

## Regression and access checks

`evidence/regression-gates/` retains before/after failures and passes for minimum/maximum nights, interval boundaries, timezone/DST calendar nights, forged website data and access restrictions. Extra company consistency and child-property access probes reproduce the former failures and pass after the separate corrections. Stored legacy icon conversion was tested against actual stored rows and rolled back (`evidence/icon-migration.json`). The source fidelity report records preserved earlier fixes and non-bot authorship.

## Adoption blockers and limits

**Concurrent bookings are unsafe.** With test mode disabled, two independent database transactions both committed confirmed reservations for the same property and interval (`evidence/concurrency.json`, reservation IDs 32 and 33). The sequential overlap correction does not serialize inventory. Production holds, payments and concurrency redesign were explicitly excluded from this migration phase. The relevant review bundles retain a high-severity adoption finding and the PRs stay draft.

**Sales-order cancellation does not propagate to its reservation.** The UI cancelled order 54 while reservation 24 stayed confirmed. The separate reservation Cancel action works. An agreed lifecycle/ownership design is required before adoption.

Container Chrome crashes under local amd64 emulation, so local server runs exclude browser/Hoot runners and two website browser classes; native Playwright/Hoot and successful fork Odoo/OCB jobs supply separate evidence. Coverage JSON is captured; a text coverage-summary subprocess crashed under emulation in one diagnostic run without failing its addon tests. Superseded diagnostic attempts are retained, including early asset contamination (removed by reassembling the hash-verified wheel), fixture-window mismatches, and one accidental concurrent test invocation. Only the final exact-head evidence above is counted as passing.

Review findings from mechanical scope and inherited AI-attribution detectors were checked against source/configuration and preserved message proofs. Raw findings and explicit adjudication decisions remain in each bundle. No PR review/comment has been posted, no upstream PR has been opened, and this evaluation is not production-ready.
