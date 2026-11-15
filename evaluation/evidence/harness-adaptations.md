The review harness is copied from `/Users/dkendall/.claude/skills/oca-review/scripts`.
Only the container coverage runner is adapted: Odoo 20 `--with-demo` replaces the removed `--without-demo=` flag, and an exact database filter is passed explicitly. The 20.0 branch uses services `odoo-prod-20` and `db-prod-20`, candidate bind mounts, synthetic databases and the pinned image. No standard ERP checkout is modified.

The regression-gate helper still contains older service assumptions. Dedicated before/after runs use this isolated 20.0 Compose stack instead; see `evidence/regression-gates/`. The generic UI helper targets port 8069; the explicit native browser walkthrough targets the dedicated localhost port 19320 and records actions/screenshots. These replacements are recorded in each review bundle, not treated as silent passes.

Later fresh reviews clone `pms20_core_template` (all 11 PMS addons explicitly uninstalled and asserted absent) to reuse core dependency/demo loading. Each review still installs its actual candidate and PMS dependency closure with `-i` into a new `oca_review_pms_prN` database. The first reviews use an entirely empty database. The database and filestore clone steps appear in each run journal; the template preparation log is retained.

The final local review runner explicitly excludes `TestPmsFrontend` and `TestWebsiteSaleCartRecovery` from the emulated container run. Their native browser evidence and fork CI are recorded separately, never counted as local container passes. All other Python and HTTP tests remain selected.
