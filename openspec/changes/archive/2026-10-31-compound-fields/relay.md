# Relay record: compound-fields

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 23963861 | 133881 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 6768409 | 44684 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | sound with reservations | 0 | 3 | 3 | 1 | 3 | 0 |
| Reviewer | one P2: an oversized pattern crashes the validator | 0 | 1 | 0 | — | 1 | 0 |

## Hand-backs

- Critic: the standalone validator ignored `format` and unknown top-level keys, and a mistyped `--settings` path declared nothing — it now applies the settings file's top-level rules, and a named settings file must exist.
- Critic: `min = nan` would disable a bound — bounds must be finite.
- Critic: no scenario showed number or boolean columns or an empty cell — scenario "Number and boolean columns" added.
- Critic (noted): the staged field data carries no ancestor keys, and reaction types need exactly one value — left to the facet and reaction-type changes.
- Test writer: built a throwaway implementation outside the repository to check its tests, beyond its brief — deleted before the implementer started; its tests were judged on their own.
- Test writer: an early draft ran the application's `clean --all` — caught by the test writer; both caches were intact.
- Implementer: settled the empty-text-under-a-pattern case (one error), the order of unknown-value errors, the shared settings check in `validate.read_settings`, and the i18n keys `boolean_yes` / `boolean_no` — accepted.
- Browser check (orchestrator, inline): the two new directory columns, kept on one line, squeezed compound names until they broke mid-word — the columns of declared fields may now wrap.
- Doc writer: recorded its run as `gpt-6` in both Org guides — corrected to `gpt-6.1-sol` with a fact-check pass line.
- Reviewer: a pattern with a huge repetition count raised `OverflowError` past the handler — reproduced, a failing test added (with deep nesting, which raises `RecursionError`), and both caught as configuration errors.

## Test boundary

held
