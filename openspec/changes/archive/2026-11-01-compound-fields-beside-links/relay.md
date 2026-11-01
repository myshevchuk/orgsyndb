# Relay record: compound-fields-beside-links

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done; amended after the critic |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 11873252 | 55048 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 968511 | 9287 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready | 1 | 3 | 4 | 0 | 4 | 0 |
| Reviewer | no actionable defects | 0 | 0 | 0 | — | 0 | 0 |

## Hand-backs

- Tests: none handed back. The test writer shared two existing copy builds (the markup build of compound-fields "Field display" and the German acetone-name build) with the new scenarios, each docstring stating why the extra change cannot touch the other's assertions; it added checks beyond the scenarios that the requirements imply (`beside = false` refused on a boolean or choice field, a non-boolean `beside` refused).
- Implementation: none handed back. Design calls settled by the implementer: `beside` is a field of the `Declaration` record, read by `declared_flag`; the partial writes the joined values through `string (delimit . ", ")`; a key with no registry entry gets the bare link; the CSS rule follows the metadata-panel rules. The orchestrator reflowed one docstring line left short.
- Docs: none corrected. The documented error messages were checked against the validator's output.
- Critic: the no-note scenario used the two-product build, whose fixture compounds gain a required `item_number` — accepted, replaced by a build that drops `beside` from `item_number`, merged with the markup scenario; the tasks did not name the tests that compare whole values — accepted, task 1.5; the metadata panel and scope table spoke of comma-joined links only — accepted, both requirements now name the note; the tasks lacked the schema documents — accepted, task 3.1.
- Reviewer: no findings.

## Test boundary

held
