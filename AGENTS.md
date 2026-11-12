# SRE Board working rules

All project content is English. Follow the PO-approved review pack v0.2.0 and
docs/approval.md; code presence and CI do not establish design or PO acceptance.

- Feature/fix PRs target develop; QA uses an exact integrated SHA, isolated source,
  configuration and database. Main is updated only by a final release PR.
- Implementation PRs count all added/deleted text lines and must stay <=500.
  Aggregate release has no automatic exemption; record actual counts and policy.
- Read every issue comment, inline thread and review submission on the latest
  head; complete reviews, disposition findings and re-review affected changes.
- Record self-review honestly. No fabricated human review, screenshot or test pass.
- Match source/runtime/evidence; preserve baseline data and historical records.
- Schema changes require versioning, existing-data preflight, a safe backup and
  migration rehearsal. Never reset main data for QA or silently repair bad rows.
- User changes are preserved. Cleanup archives superseded records; do not rewrite
  main history or delete traceability evidence.
- New product scope and policy exceptions require explicit decisions. Routine
  implementation within accepted scope/design is delegated by GOV-01.
