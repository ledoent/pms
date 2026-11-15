This branch combines the eleven Odoo 20 PMS migrations and the four separately reviewed
booking fixes. It is a fork-only evaluation build; it is not approved for adoption.
Exact source SHAs, wheel hash and container image digests are in
`evaluation/evaluation-lock.json`.

On a clean host with Docker and Python 3.12+, run
`python3 evaluation/scripts/init_evaluation.py --tests`, then seed the synthetic UI
database with the shell script and start the UI service as described in
`evaluation/README.md`. No GoTime schemas or synchronization are added.

The independent-transaction probe reproduced two committed confirmed bookings for the
same property and dates. Cancelling a sale order also leaves its reservation active
until explicitly cancelled. These are adoption blockers/gaps; production inventory
holds, payments and lifecycle redesign are outside this branch.

AI-assisted (Codex). Original source authorship is preserved in the individual migration
PRs linked in `evaluation/pull-requests.json`.
