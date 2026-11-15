Every addon was replayed from `ledoent/pms:19.0` at
`50919859db16540d13dd90bc1bd89c8a30ddf4c3` onto upstream’s empty Odoo 20 scaffold
`e611cc04820b0c8abd6e2dc7f4dc82c531b791d2`.

For each addon, `evidence/<addon>/replay.json` records identical source and replay Git
tree IDs before mechanical linting or compatibility work. `commits-pre.tsv`,
`commits-post.tsv`, `classes.tsv`, `folds.txt`, `preservation.log`, the mailbox and
replay log preserve the replay audit. The bot-squash gate reports that every
non-squashable commit and author is preserved. Translation commits remain attributed to
their translators.

Mechanical `[IMP]` commits precede substantive `[MIG]` commits; temporary
`[DO NOT MERGE]` commits contain immutable dependency pins. New authored commits use
`Assisted-by: Codex`, and fork PR descriptions identify Codex assistance. Some original
19.0 commits already contain AI coauthor trailers; those are retained as historical
authorship, not attributed to this implementation. The static review’s C29 flags on
those replayed commits are documented as inherited attribution, not silently removed.

## Replayed fixes checked

- `47ee456`, booked-by propagation from the sale-order configurator: the model wizard
  field, default propagation, XML required field and partner regression tests remain.
  The Owl 3 controller includes the booked-by partner in created/updated reservation
  values. The sale description and explicit product field both route to the PMS
  configurator in Odoo 20.
- `ff6c17e`, removal of an unused configurator-test product fixture: retained; no legacy
  fixture was reintroduced.
- `4160359`, property detail and listing repair: listing/detail routes, published demo
  properties, images, categories/amenities and the HTTP/unit tests remain. Odoo 20
  request/environment APIs were adapted. Website security/input corrections are separate
  fix PRs.
- OCA/pms#444, original minimum-night correction
  `65de281d175d0de5023bede4322c93effb07c335`: cherry-picked separately with Bertrand
  Retif’s authorship and commit message retained. The three original regression cases
  fail against the migration baseline and pass with the fix.

The stored Font Awesome-to-Material conversion is an intentional migration of persisted
icon values. ACL/rule XML becomes Odoo 20 `ir.access`; obsolete file removals represent
converted definitions, not a lost permission file. The published `web_timeline` wheel is
used byte-for-byte: both assembled copies are checked against its locked wheel hash in
`evidence/wheel-integrity.json`.

The initial timeline error and speculative shim captures are diagnostic failures from an
earlier, contaminated evaluation dependency tree. They are superseded by clean-source
assembly and final browser/test evidence. The speculative shim is absent from migration
code and from the final assembly.
