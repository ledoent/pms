# PMS 20.0 fork evaluation

Eleven PMS addon migrations and four separate booking-fix PRs are implemented for
Odoo 20. The evaluation uses exact Git SHAs, a hash-verified published `web_timeline`
wheel, pinned container images, synthetic databases and dedicated volumes.

**Adoption is blocked.** Independent transactions both committed confirmed reservations
for the same property and dates. Cancelling a sales order also leaves its reservation
active until the reservation is explicitly cancelled. See
[GoTime fit/gap report](GOTIME-FIT.md) and [validation evidence](VALIDATION.md).
GoTime’s existing models remain canonical; no synchronization, upstream submission or
production rollout is included.

## Deliverables

- [Migration and fix PR index](pull-requests.json): draft PRs 1–15 in
  [ledoent/pms](https://github.com/ledoent/pms/pulls).
- Combined source branch:
  [20.0-evaluation](https://github.com/ledoent/pms/tree/20.0-evaluation).
- [Immutable evaluation lock](evaluation-lock.json),
  [migration heads](migration-lock.json), [separate fix heads](fix-lock.json),
  [dependency audit](evidence/dependency-review.json).
- [Source history and attribution](SOURCE-FIDELITY.md),
  [effective access review](ACCESS-REVIEW.md), [GoTime fit](GOTIME-FIT.md).
- Per-candidate `oca-review` bundles linked in [REVIEW-INDEX.md](REVIEW-INDEX.md), including frontend
  critiques, logs, coverage, screenshots, findings adjudication, a draft review body,
  manifest and verification script. Review comments are not posted.
- [Evaluation verification](verify_evidence.py) checks the sealed workspace evidence;
  each review bundle also has its own `verify.sh`.

## Reproduce on a clean host

Requires Docker Compose and Python 3.12+. These commands operate only on this evaluation
project. The prepared local UI uses `http://127.0.0.1:19320`, synthetic `admin` /
`admin`, database `pms20_ui`, and services `odoo-prod-20` / `db-prod-20`.

```sh
python3 scripts/init_evaluation.py --tests
# The initializer refuses to overwrite an existing database.
docker compose -f docker-compose.20dev.yml run --rm --no-deps odoo-prod-20 \
  odoo shell -d pms20_ui --db-filter='^pms20_ui$' --no-http < scripts/seed_ui.py
docker compose -f docker-compose.20dev.yml up -d odoo-prod-20
```

The initializer assembles sixteen addon sources from the lock and performs real
installation of the eleven PMS addons. Use `--database pms20_another_name` for an
additional fresh database; the UI service selects `pms20_ui` by default.
`scripts/assemble.py --migration-only` reconstructs the migration-only assembly;
`PMS_ADDONS_DIR=./addons` selects it for a Compose invocation. The default is the
corrected `addons-fixed` assembly. No source directory from a GoTime checkout is
mounted.

The local server test selection excludes the emulated container’s browser classes and
Hoot cross-module browser runners. Their results are kept separate: native browser/Hoot
evidence and fork Odoo/OCB CI. No zero-test run counts as a pass.

## Native browser checks

```sh
python3 -m venv .runtime/browser
.runtime/browser/bin/pip install -r browser-requirements.txt
.runtime/browser/bin/python -m playwright install chromium
.runtime/browser/bin/python scripts/ui_probe.py --hoot --name hoot-reproduced
```

`scripts/ui_probe.py` accepts explicit observed UI actions through `--actions`; actual
walkthrough action lists and results are in the published review bundles.
the workspace UI seed evidence identifies the synthetic records and menu actions. Desktop and
mobile Hoot presets are supported. The UI evidence covers property creation, reservation
configuration/save, timeline filters, order confirmation, invoice creation, explicit
reservation cancellation and website cart booking; the validation report records the
exact completed captures and limitations.

The independent-transaction probe is intentionally separate from test-mode transactions:

```sh
docker compose -f docker-compose.20dev.yml run --rm --no-deps odoo-prod-20 \
  odoo shell -d pms20_ui --db-filter='^pms20_ui$' --no-http < scripts/concurrency_probe.py
```

## Dependency and review scope

External sources are `contract` from OCA/contract#1566, the asset-management fork PR
#13, its XLSX reporting closure, and the published `web_timeline` 20.0 wheel. Exact
commits and hashes are authoritative; moving branches are not used by the assembler.
Expected unreleased-dependency checks remain red while these sibling/fork sources are
unmerged. The external contract PR’s CLA check is separate from its passing functional
jobs.

The review harness is a task-local copy of `oca-review`, adapted for Odoo 20’s demo
flag, exact database filters, these service names, isolated clean-core templates and
native browser evidence. See [harness changes](evidence/harness-adaptations.md). Failed
diagnostic attempts remain in the evidence; final passes, superseded attempts and
blocked checks are distinguished in [VALIDATION.md](VALIDATION.md).

New implementation and review preparation are AI-assisted (Codex). Original replayed
authorship, including the minimum-night fix from OCA/pms#444, is retained.
