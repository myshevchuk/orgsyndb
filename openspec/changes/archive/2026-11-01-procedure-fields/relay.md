# Relay record: procedure-fields

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 18193621 | 102708 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 6210318 | 38917 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run (first run stopped by the harness under memory pressure, no report; re-run) |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready: Org typing contract and reserved keys had gaps | 1 | 2 | 0 | 0 | 3 | 0 |
| Reviewer | scenarios satisfied; one test passes for an unrelated error | 0 | 1 | 0 | — | 1 | 0 |

## Hand-backs

- Tests: required values across language variants are not specified per file — left untested; each file is checked on its own.
- Implementation: `test_facet_and_multiple_are_taken_as_declared` declared the reserved key `kind` — test corrected by the orchestrator.
- Implementation: three uniqueness tests copied a baseline that already held the keys they added, so the copy failed to parse — test corrected by the orchestrator (copy before setting the values).
- Implementation: `test_procedure_declarations_declare_no_compound_field` declared the compound field it meant to leave undeclared — test corrected by the orchestrator.

## Test boundary

held
