# SRE Board

A real local pilot validating SDLC with coding agents: versioned requirements,
Jira work items, small GitHub PRs, real SQLite/HTTP tests, browser screenshots,
technical self-review and honest acceptance/release evidence.

## Run locally
Requirements: Python 3.11+; no Python packages required. Node 22+ for JS unit checks.
Start from the repository root. Configure distinct local credentials before startup:

```sh
export SREB_WEBHOOK_TOKEN='replace-with-a-local-secret-at-least-16-characters'
export SREB_OPERATOR_TOKEN='replace-with-a-different-local-secret-at-least-16-characters'
export SREB_DB='sreboard.sqlite'
python3 -m sreboard.server
```

Open http://127.0.0.1:8765. Enter the operator token; it stays in tab memory only.
The server binds loopback only. These sample strings are instructions, not deployed
credentials. The pilot is not an internet-facing production server.

## Ingest an alert
```sh
curl --fail-with-body http://127.0.0.1:8765/api/webhook \
  -H "Authorization: Bearer $SREB_WEBHOOK_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"orders-001","title":"Pipeline delayed","pipeline":"orders","severity":"P1"}'
```

New → Acknowledge → Investigating → Monitoring → Resolved. Resolved leaves the
active report; SQLite retains the alert and history. Use a known alert ID in
“View retained history” to inspect it after resolution. Severity is independent.
Exact duplicates return the same alert; conflicting payloads/version updates return 409.

## Verify
```sh
python3 -m compileall -q sreboard tests
python3 -m unittest discover -v
node --check static/app.js
node --test tests/ui.test.cjs
```

Python tests use disposable real SQLite files and actual loopback HTTP, no API mocks.
JS regression tests use a minimal DOM/fetch double; they do not prove browser rendering.
Actual browser evidence and exact-source run records are recorded separately.
Tests require permission to bind loopback; an unavailable environment is not a pass.

## Project records
- [Charter and actual roles](docs/charter.md)
- [Requirements and contract](docs/requirements.md)
- [PO decision record](docs/decisions.md)
- [Risk-to-test plan](docs/verification-plan.md)
- [Jira epic SREB-1](https://nhanlagc60299.atlassian.net/browse/SREB-1)

Every PR counts additions + deletions of text files and must stay <=500 lines.
Binary screenshots need separate visual review; they are not code-line evidence.
CI runs syntax and domain/HTTP/JS regression checks, not browser E2E.

## Scope and honesty
PO: Anh Nhan Le. Implementation/testing/technical review: Codex, explicitly delegated.
No independent human review is claimed; API writes use the connected owner's identity.
PO business acceptance and external production release are separate, not implied by CI.
No production deployment exists; do not confuse main's tip with a deployed baseline.
README-only seed initializes an originally empty repository; later changes use PRs.
