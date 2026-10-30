# Relay record: general-procedures

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 37483167 | 164698 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 14034881 | 64596 | done: resumed once after a usage-limit stop |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | re-run: first run exited 1 with no report |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready | 4 | 3 | 3 | 1 | 7 | 0 |
| Reviewer | no actionable defects; 97 of 103 scenarios tested | 0 | 0 | 0 | — | 0 | 0 |

## Hand-backs

- Critic: the union rule reached the substrate-is-product check across entries — validation made per entry, the union kept for display, links and indexes.
- Critic: the ninth demo procedure changed counts, chains and a SMILES result the deltas did not carry — the scenarios amended in localization, site-theme and site-search.
- Critic: the export's problem list and the validator's field forms did not admit scope problems — both contracts amended.
- Critic: tomelr would nest an entry's later keys in its last product — each entry's `products` written last.
- Critic: the German shell scenario did not exempt `/general-procedures/` — exempted.
- Critic: sharing `scope` made notes untranslatable — notes excepted from the comparison.
- Test writer: fixed a serve test that blocked 600 s on a failed build — accepted as a harness fix.
- Implementer: the export test expected unpadded table separators, which ox-hugo never writes — test changed to match separator lines by pattern.
- Implementer: the title-key count did not include `/general-procedures/` — test changed to seven.
- Implementer: a column named twice got a message the spec lacked — spec amended to list it.
- Implementer: `pipeline.py` did not read `scope` as a field of an Org error — fixed in line with org-export.
- Orchestrator: the scope table wrapped `30 min` in a narrow Time column — numbers, scales and times kept on one line.

## Test boundary

crossed: tests/test_export_integration.py, tests/test_localization.py — changed by the orchestrator after the implementer handed both back as wrong; the implementer changed no test
