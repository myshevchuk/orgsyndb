# Relay record: procedure-widgets

| Stage | Agent | Assignment | Model requested | Model recorded | Effort requested | Effort recorded | Uncached input | Cache writes | Cache reads | Output | Start | End | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | proposal, design, tasks, site-theme and localization deltas | claude-opus-5-5 | claude-opus-5-5 | high (switch not asked of the operator) | medium | 49 | 78365 | 3079435 | 29753 | 2026-11-22T20:44:39.503Z | 2026-11-22T20:49:31.761Z | done |
| 2 Critic | agy critic | the change; doubts on the `.Content` split, figures in the article, uncovered specs and tests, the notes grid | gemini-4-neon-high | — | high | — | 0 | not recorded | 2600183 | 36042 | 2026-11-22T20:49:31.761Z | 2026-11-22T20:58:03.139Z | run |
| 3 Tests | test-writer | tasks 1.1–1.4, checked against a throwaway prototype | sonnet | claude-sonnet-5-5 | high | high | 148 | 206039 | 10958683 | 61598 | 2026-11-22T20:58:03.139Z | 2026-11-22T21:17:51.492Z | done |
| 4 Implementation | ui-specialist (agy) | tasks 2 and 3: procedure templates, sections partial, i18n, screen.css, print.css | gemini-4-neon-medium | — | medium | — | 0 | not recorded | 1068191 | 26874 | 2026-11-22T21:17:51.492Z | 2026-11-22T21:27:35.236Z | done; orchestrator raised the `.procedure-section` specificity after the browser check (prose was 13 px) |
| 5 Docs | orchestrator, inline | figure and panel paragraphs of the four authoring guides | claude-opus-5-5 | claude-opus-5-5 | medium | medium | 20 | 12640 | 2451431 | 6239 | 2026-11-22T21:27:35.236Z | 2026-11-22T21:28:36.983Z | inline: docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | c90ceff...HEAD against the change | gpt-6.2-sol | — | xhigh | — | not recorded | not recorded | not recorded | not recorded | 2026-11-22T21:28:36.983Z | 2026-11-22T21:36:50.058Z | run |

## Routing

question 3: UI-focused (templates, layout, print styling) → ui-specialist, gemini-4-neon-medium · re-routes: none

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready | 4 | 2 | 4 | 3 | 9 | 1 (part of B3: splitting only at top-level `h2`; nested headings recorded as an accepted risk) |
| Review | not ready | 0 | 6 (4 P2, 2 P3) | 0 | — | 5 | 1 (nested `##` in a block quote: accepted risk in design.md) |

## Hand-backs

- none. Review fixes (label column, notes span guard, Unicode spaces in section names, print title with first figure, "up to three boxes" in the guides) were made inline by the orchestrator, per the owner's rule for small post-review fixes.

## Test boundary

held
