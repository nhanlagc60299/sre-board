# Database design and migration — DATA-01 / DATA-03

Approved design: review pack v0.2.0, PO 2026-11-12. Implementation task SREB-10.
SQLite version 1 retains alerts (id PK, event_id unique, current state/version)
and history (seq PK, alert_id FK, unique alert_id+version). FK enforcement is
enabled on each application connection. CHECKs enforce permitted states/severity,
positive integer versions and bounded text lengths. Store/API still validate
printable normalized text and legal transitions; DB column checks alone do not
prove complete history or business correctness.

Creation and transition use BEGIN IMMEDIATE; list/detail use read transactions.
No reopen/delete or personal audit identity. No speculative query indexes added.

## Explicit legacy migration
Startup initializes an empty database only. A version-0 database fails closed;
do not make an automatic startup upgrade or change main data during a QA run.
Stop the affected pilot instance and rehearse on a SQLite-consistent copy first:

`python3 -m sreboard.migrate /path/to/copy.sqlite --backup /path/to/new-backup.sqlite`

The backup destination must be new. Preflight rejects unknown schema objects,
invalid/orphan/inconsistent history and invalid text without normalization or
repair. The real SQLite backup is integrity-checked, then content is compared
again under the migration write lock to detect intervening writes. Schema/data
copy, equality checks and version marker commit atomically; any failure rolls back.
Retain failed-run evidence and the backup; retry only after investigating the cause.

Technical clarification under GOV-01: legacy migration is an explicit offline
operation. Version 1 is PRAGMA user_version=1; unknown/future versions fail closed.
Preserve every column value and sequence. Tests use a controlled failure hook for
rollback, but real SQLite for all data/schema operations; this is disclosed injection.

Restore uses the backup plus compatible old source/config; code revert alone is
insufficient. Never restore QA data over main. Restoring an old backup may lose
later writes and needs a concrete recovery decision. Long-term production
retention/backup remains outside the local pilot. No main migration is claimed here.
