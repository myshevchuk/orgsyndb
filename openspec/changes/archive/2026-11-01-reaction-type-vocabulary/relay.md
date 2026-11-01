# Relay record: reaction-type-vocabulary

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done; amended after the critic |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 13778322 | 67267 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 2696407 | 14555 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | re-run: the first two calls hit the Codex usage limit and wrote nothing; third run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org (docs/AUTHORING.md left unchanged as already correct) |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | sound with reservations | 0 | 2 | 4 | 1 | 2 | 0 |
| Reviewer | no runtime defect; two non-blocking findings | 0 | 2 | 0 | — | 1 | 1 |

## Hand-backs

- Tests: none handed back. One assertion of the test writer (the reaction-type data keeps the file's key order) went beyond the spec — removed by the orchestrator before the baseline commit.
- Implementation: none handed back. Design calls settled by the implementer: the `parent` refusal runs after `load_terms`; declarations load before the reaction types, so a declaration naming `reaction-types` keeps the missing-vocabulary error; the path is the constant `validate.REACTION_TYPES`; the label partial tolerates absent data. The orchestrator removed the now unused `validate.APP`.
- Docs: the doc writer recorded `gpt-6` in both Org guides' pass lines — corrected to the pinned model with a fact-check pass line. Its two new Org links used a `file:…::search` target, which help pages render as plain text, and the German search string matched text before the heading — replaced by plain file links, together with the two such links of the procedure-fields change.
- Critic: a declared field naming `reaction-types` against "a missing file is no error" — accepted, declarations win, two scenarios added; the test task missed tests that leaned on the application's list implicitly — accepted, task 1.1 broadened.
- Reviewer: P2, the living specs still name `--vocabulary` and `site/data/reaction_types.toml` — rejected, the living specs take the deltas on archive; P3, the first-stub test passed when validation aborted — accepted, it now requires exit status 0.

## Test boundary

held
