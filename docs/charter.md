# SRE Board — project charter

Version: 0.2, 2026-11-11. Tracking: SREB-1 / SREB-2.
Repository: https://github.com/nhanlagc60299/sre-board

## Verified starting point
- Jira SREB had no issues; GitHub had no commits/branches at discovery.
- GitHub default-branch metadata was `main`, not `master`.
- README-only seed `cad73960e36771a4a4226922ff2141dcdaa64550` establishes a PR base.
- Seed is documentation only, not product code or a reviewed deployment.
- No actual production, UAT deployment, or deployed baseline exists yet.

## Confirmed scope and real roles
The PO explicitly selected the handbook case: webhook alerts, P1–P4 severity,
active report, and Acknowledge → Investigating → Monitoring → Resolved.
Resolved alerts leave the report; disappearance does not imply deletion.

| Role | Actual actor | Authority/evidence |
|---|---|---|
| PO and business decision maker | Anh Nhân Lê (`nhanlagc60299`) | Confirmed in this chat, 2026-11-11 |
| Feature implementation owner | Codex coding agent supporting the repo owner | Delegated by the PO |
| Technical design/testing/review | Same Codex coding agent | PO explicitly delegated technical review |
| Independent human technical reviewer | None assigned | Do not invent a reviewer or approval |
| Business acceptance | Anh Nhân Lê | Pending demonstration and explicit response |
| External production release approval | Not delegated | No public production deployment assumed |

GitHub/Jira writes use the connected owner's account. That transport identity
must not be misrepresented as the PO having authored, reviewed, or approved code.
Agent technical review is recorded as self-review with correlated-error risk.

## Working agreement
- Work on separate PR branches; count additions + deletions across all text files.
- Keep every PR <=500 changed lines, including tests/config/docs; no silent exemption.
- PRs may depend on earlier open PRs. Record base/head and integration ordering.
- Track Draft and waiting work; finish current slice before starting another.
- Do not mark business acceptance/release done from test results alone.
- Use actual tool logs, exact SHA, environment, real dependencies, and screenshots.
- Local pilot delivery is not a public production deployment.
- No fabricated screenshots, people, successful runs, or reviews.

## Technical implementation choice (agent decision)
Use Python 3.11+ standard library, SQLite, and a small native HTML/CSS/JavaScript UI.
This keeps the pilot reproducible without external service credentials/dependencies.
Use unittest for domain/HTTP integration checks and browser automation for E2E
when an available browser runtime supports it. SQLite is a real test dependency.
This is a local pilot, not a claim that a stdlib HTTP server is internet-ready.
Do not bind publicly; require separate tokens for webhook and operator API.

## Delivery gates
1. PO confirmed D1–D10 for the local pilot; see `decisions.md`.
2. Version code/contracts/tests and actual execution evidence.
3. Technical self-review and tracked corrections; disclose no independent human review.
4. Demonstrate running app and obtain actual PO business acceptance.
5. Reconcile the final candidate and local artifact; label external deployment unperformed.
6. Feed observed process gaps back into both handbook editions.
