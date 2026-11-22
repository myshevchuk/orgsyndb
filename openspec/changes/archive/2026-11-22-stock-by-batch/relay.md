# Relay record: stock-by-batch

| Stage | Agent | Assignment | Model requested | Model recorded | Effort requested | Effort recorded | Uncached input | Cache writes | Cache reads | Output | Start | End | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | proposal, design, tasks, deltas for end-product-inventory, lab-demo, database-diagram; amended for postgresql-only and lab.js narrowing | claude-opus-5-5 | claude-opus-5-5 | high | high | 176 | 200232 | 14330260 | 71117 | 2026-11-22T09:20:00.000Z | 2026-11-22T10:26:48.679Z | done |
| 2 Critic | codex critic | change and five named doubts (line identity readers, assignment counting, lock order, restatement fidelity, demo satisfiability) | gpt-6.2-astra | — | medium (operator override of high) | — | 65369 | 0 | 892416 | 4607 | 2026-11-22T10:26:48.679Z | 2026-11-22T10:31:20.349Z | run |
| 3 Tests | test-writer | tasks 1.1–1.6 against a stated interface contract | definition default | claude-sonnet-5-5 | definition default | high | 326 | 510913 | 49517681 | 229739 | 2026-11-22T10:31:20.349Z | 2026-11-22T11:15:49.356Z | done |
| 4 Implementation | local-implementer | tasks 2.1–2.8, all non-test files of inventory, planning readers, demo, diagram, lab.js, catalogue | definition default | claude-sonnet-5-5 | definition default | high | 218 | 533058 | 25722977 | 102226 | 2026-11-22T11:15:49.356Z | 2026-11-22T12:39:40.322Z | done; stopped for a quota pause and resumed with its context |
| 5 Docs | codex doc writer | update README.md: overview, items, deliveries and corrections, filling, admin, demo | gpt-6.2-sol | — | high | — | 67533 | 0 | 877696 | 8780 | 2026-11-22T12:40:25.455Z | 2026-11-22T12:44:51.064Z | run: README.md |
| 6 Review | codex reviewer | 8a1ebb7...HEAD, change stock-by-batch | gpt-6.2-sol | — | xhigh | — | not recorded | not recorded | not recorded | not recorded | 2026-11-22T12:44:51.064Z | 2026-11-22T12:51:00.995Z | run |

## Routing

question 5: local-implementer; the design was settled, but correctness turns on the lock order and refusal paths across fill, book_note, correct and reverse · re-routes: none

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | Not ready | 6 | 3 | 0 | 0 | 9 | 0 |
| Review | patch is incorrect | 0 | 6 | 0 | — | 4 | 2 |

## Hand-backs

- 3 Tests: count location on pages is heuristic (name before count) — kept; the implementer told to put the name first
- 3 Tests: `unbekannt` absent outside the ledger when the unknown share is zero — kept
- 3 Tests: a row with only a batch left untested — accepted; the review later had the form mark every missing field

## Test boundary

held
