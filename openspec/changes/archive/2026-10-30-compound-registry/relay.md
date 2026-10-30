# Relay record: compound-registry

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | run |
| 3 Tests | test-writer | sonnet | claude-sonnet-5-5 | high | high | 34108744 | 159292 | done |
| 4 Implementation | implementer | opus | claude-opus-5-5 | medium | medium | 12878991 | 62032 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | sound with reservations | 0 | 3 | 3 | 1 | 3 | 0 |
| Reviewer | one P2: compound names escaped twice | 0 | 1 | 0 | — | 1 | 0 |

## Hand-backs

- Critic: the working-directory scenario could not pass with relative fixture paths — given absolute registry and static paths.
- Critic: the overlay contract still counted four mounts — corrected to six.
- Critic: manual checks the change alters were missing from tasks — added to task 3.2 (the inherited "section 6" references were left as they are).
- Proposal: the theme fixtures' compounds were named in two places — kept in the fixture registry only.
- Implementer: the export also requires `tomelr-toml-table-array-p`, one function beyond the spec's check — spec amended to name it.
- Doc writer: recorded its run as `gpt-6` in both Org guides — corrected to `gpt-6.1-sol` with a fact-check pass line.

- Reviewer: compound names were escaped twice in titles and headings — reproduced with an apostrophe name, a failing test added, the partial made to return a plain string.

## Test boundary

held
