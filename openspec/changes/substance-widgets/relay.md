# Relay record: substance-widgets

| Stage | Agent | Assignment | Model requested | Model recorded | Effort requested | Effort recorded | Uncached input | Cache writes | Cache reads | Output | Start | End | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | proposal, design, tasks, lab-registry delta | claude-opus-5-5 | claude-opus-5-5 | high | not recorded | not recorded | not recorded | not recorded | not recorded | 2026-11-22T18:22:38.438Z | 2026-11-22T18:24:16.515Z | done |
| 2 Critic | agy critic | substance-widgets; doubts on completeness of the rewritten requirement, layout in spec, other dependants, unsortable tables | gemini-4-neon-high | — | high | — | 0 | not recorded | 2468374 | 38485 | 2026-11-22T18:24:16.515Z | 2026-11-22T18:32:42.989Z | run; no second pass, the rework being moderate |
| 3 Tests | test-writer | tasks 1.1–1.3 | sonnet | claude-sonnet-5-5 | high | high | 64 | 130174 | 2620388 | 40589 | 2026-11-22T18:32:42.989Z | 2026-11-22T18:42:00.918Z | done |
| 4 Implementation | agy ui-specialist | tasks 2.1–2.2; substance.html, screen.css, lab.css, registry catalogue | gemini-4-neon-medium | — | medium | — | 0 | not recorded | 2079787 | 23431 | 2026-11-22T18:42:00.918Z | 2026-11-22T18:49:42.809Z | done |
| 5 Docs | orchestrator, inline | docs/SCHEMA.md, docs/SCHEMA.de.md: order of the substance page's parts | claude-opus-5-5 | claude-opus-5-5 | medium | not recorded | not recorded | not recorded | not recorded | not recorded | 2026-11-22T18:49:42.809Z | 2026-11-22T18:50:51.545Z | inline: one sentence in each guide |
| 6 Review | codex reviewer | 77ca525..fe2825f, substance-widgets | gpt-6.2-sol | — | xhigh | — | not recorded | not recorded | not recorded | not recorded | 2026-11-22T18:50:51.545Z | 2026-11-22T18:54:55.946Z | run |
| 4 Implementation | orchestrator, inline (review fixes) | the three accepted review findings in lab.css | claude-opus-5-5 | claude-opus-5-5 | medium | not recorded | not recorded | not recorded | not recorded | not recorded | 2026-11-22T18:54:55.946Z | 2026-11-22T18:56:24.264Z | done; the owner asked for small post-review fixes inline, so lab.css has two authors (Google, Anthropic), both outside the reviewer's family |

## Routing

question 3: UI-focused (template, CSS, catalogue) → ui-specialist, gemini-4-neon-medium · re-routes: none; post-review fixes inline by the orchestrator at the owner's instruction

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic (agy) | not ready | 3 | 5 | 4 | 1 | 8 | 0 |
| Review | 3 findings, none blocking | 0 | 3 | 0 | — | 3 | 0 |

## Hand-backs

- 3 Tests: five readings left open (note label, figure before table, `–` for an empty status, narrow `dl.metadata` check, Hugo comparison left to the procedure change) — accepted as written.
- 4 Implementation: the implementer listed docs/SCHEMA.md and SCHEMA.de.md as affected — edited inline in stage 5.

## Test boundary

held
