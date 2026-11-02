# Relay record: derived-synthesis-routes

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done; amended after the critic |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 6732616 | 58318 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 1844481 | 20977 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run; the first run was stopped for low memory before it reported, the second, asked to skip builds, completed |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready | 2 | 3 | 6 | 0 | 5 | 0 |
| Reviewer | ready, no actionable defects | 0 | 0 | 0 | — | 0 | 0 |

## Hand-backs

- Tests: none handed back. The test writer added a build per test for the staged route data, as its neighbouring staging tests do; accepted. It fixed the OSDB-0910 yield (95) and the generated chain's title, which the spec leaves open.
- Implementation: none handed back. Design calls settled by the implementer: the depth-1 tree is built uncapped and each deeper tree is abandoned once it passes the budget; deepening stops when a tree cuts nothing off; result keys are sorted; missing keys raise `KeyError`; the template maps IDs to pages with a scratch map once per page; the tree's nested lists drop their markers and indent by a rule line.
- Docs: the doc writer marked that the notes called 200 steps an absolute maximum while the spec keeps the first level whole; the orchestrator added that exception to all seven documents and removed the markers. Both Org pass lines named `gpt-6` and were corrected to the run model, with a fact-check pass line.
- Critic: the validator spec reads only `fields` from the settings — accepted, made moot by dropping the setting; the aspirin scenario expected `Draft` where the English badge is `draft` — accepted; general-procedures pools the substrates of all entries — accepted, routes excepted in "Scope entries"; the depth limit does not bound a tree's size, and a setting was not justified — accepted, fixed depth 6 with a 200-step budget; the print non-goal was unbacked — accepted, removed.
- Reviewer: no findings.

## Test boundary

held
