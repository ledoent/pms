PMS 20.0 is an isolated evaluation candidate. GoTime’s existing property and campground
models remain canonical. No synchronization, replacement schema, production rollout,
payment integration or inventory-hold redesign is included.

## Adoption decision

**Blocked: concurrent bookings can overbook a property.** The independent-transaction
probe created two confirmed reservations for the same property and exact interval. Both
constraints completed before either transaction committed; both commits succeeded. See
[machine-readable result](evidence/concurrency.json), [log](evidence/concurrency.log)
and [reproduction](scripts/concurrency_probe.py). The ordinary overlap constraint
prevents sequential conflicts but provides no transaction-level inventory exclusion.
Draft cart reservations also do not reserve inventory.

The separate booking fixes are required for evaluation of minimum nights, local calendar
nights/DST, half-open checkout boundaries, company isolation, public listing permissions
and guest payload validation. Migration-only branches intentionally retain these source
defects for separately reviewable fixes. Neither migration-only nor corrected PMS is
approved for production adoption.

## Conceptual resource mapping

| PMS                                                               | Canonical GoTime concept                                                      | Fit and gap                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `pms.property`, delegated `res.partner`, optional parent/children | `property.unit`; `campground.park`, `campground.site`, `campground.site.type` | PMS provides catalog, address, rooms, amenities and publication. A partner record is not an authoritative unit/site identity. Parent-child listings are not park/site inventory rules. Mapping would require an explicit later ownership boundary; no mapping tables are added here. |
| `pms.reservation`, `pms.stage`, property reservation type/product | `campground.reservation`, `campground.reservation.night`                      | PMS stages and sale links support a basic hospitality workflow. GoTime has controlled lifecycle transitions, expiring holds, request idempotency, quote fingerprints and per-night inventory. PMS lacks equivalent atomic inventory/hold behavior.                                   |
| PMS owner partner and property team                               | GoTime ownership, management agreement, owner account/transaction/statement   | A single owner partner cannot represent effective-dated fractional ownership, management terms, statement allocation or payout obligations. Teams and accounting links are useful UI organization only.                                                                              |
| PMS contract service and recurring contract invoice line          | `property.lease` plus lease schedules, payers, memberships, accounting inputs | Recurring invoice generation is useful operational billing, but does not establish lease classification, collectibility, commencement, frozen accounting assumptions, deferred income or initial direct cost treatment.                                                              |
| PMS property asset link to OCA `account.asset`                    | GoTime property asset and lease/accounting control boundaries                 | The OCA depreciation relationship can identify equipment attached to a property. It does not replace lease accounting, commencement controls or GoTime asset ownership/valuation policy.                                                                                             |
| PMS sale order/invoice/reservation line                           | GoTime reservation billing and property funds/trust controls                  | Standard commercial invoices are a partial fit. Deposits, trust receipts, disbursements, restricted balances and reconciled owner liabilities need their existing GoTime controls. PMS cart creation is not an authorized payment or trust-fund event.                               |
| PMS guest rows, booked-by partner, website account                | GoTime verified guest challenge and guest journey                             | Booking inputs now use a strict field allowlist, publication/company scope and related-rate validation. PMS lacks the verified guest challenge, consent/identity workflow and controlled guest lifecycle of GoTime. No cross-system portal access is granted.                        |
| PMS tasks, leads, stock locations and purchase links              | GoTime property operations and maintenance/procurement                        | Useful operator conveniences. They require later policy around canonical asset/site identity, maintenance service state, company isolation and purchase authorization.                                                                                                               |

## Lifecycle and date semantics

Corrected PMS uses `[checkin, checkout)` intervals: checkout at the next arrival
boundary does not overlap; confirmed/booked operational stays block sequential
conflicts; new and cancelled stays do not. Nights are calendar-date differences in the
property timezone rather than rounded UTC hours. Check-in/out defaults are converted
from property-local time to naive UTC for Odoo storage. The evaluation covers
spring/autumn DST, adjacent stays, reversed dates, min/max bounds, capacity and
cross-company visibility.

GoTime’s lifecycle includes draft, hold, confirmed, in-house, done, cancelled and
expired states with controlled transitions and immutable quoted terms. A generic
writable PMS stage is not interchangeable with that state machine. The concurrency probe
is a distinct remaining correctness defect even after all sequential date tests pass.
The UI also reproduced that cancelling a linked sale order does not automatically cancel
its reservation; the reservation must be cancelled separately through its Cancel action.
This lifecycle coupling is an additional adoption gap, not silently redesigned in the
migration.

## Accounting, owners and billing

Keep `property.lease` and its schedules/frozen input versions authoritative for lease
accounting. Keep the GoTime owner accounts, ownership records, management agreements and
statements authoritative for owners. Keep property-funds transactions authoritative for
deposits and trust disbursements. A PMS reservation, contract or sale invoice must not
silently create or supersede any of those obligations.

The evaluation exercises PMS contract/property invoice-line attribution, asset links and
depreciation, property tasks, purchase lines and stock routing in the combined stack.
Those results establish addon compatibility, not accounting-policy equivalence. Source
review is not a legal/accounting-policy opinion.

## Evidence and provenance

GoTime source was inspected read-only in
`../gotime/property-parity-worktree/odoo/custom/src/private`:
`gt_property_lease/models/{lease,schedule,domain}.py`;
`gt_property_management/models/{property_ownership,owner_account,owner_transaction,owner_statement}.py`;
`gt_property_funds`; `gt_property_asset`; `gt_property_operations`;
`gt_campground_base/models/campground.py`;
`gt_campground_reservation/models/reservation.py`;
`gt_campground_guest/models/{challenge,users}.py`. These are current local
implementation observations; no behavior of a production deployment is inferred.

Exact PMS migration, correction, external dependency and image versions are recorded in
[evaluation-lock.json](evaluation-lock.json). See [validation evidence](VALIDATION.md),
[draft PR index](pull-requests.json), and the per-addon review bundles under `reviews/`.
Source commit authorship and prior fixes are retained; newly authored implementation and
review preparation are AI-assisted (Codex).
