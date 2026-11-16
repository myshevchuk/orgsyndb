# Relay record: retire-compound-pages

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | medium (operator override of high) | not read | not read | not read | run |
| 3 Tests (lab) | test-writer | claude-sonnet-5-5 | claude-sonnet-5-5 | high | high | 1206832 | 14819 | done |
| 3 Tests (site, build) | test-writer | claude-sonnet-5-5 | claude-sonnet-5-5 | high | high | 23661911 | 61382 | done |
| 4 Implementation (lab) | implementer | claude-opus-5-5 | claude-opus-5-5 | medium | medium | 903268 | 7589 | done |
| 4 Implementation (site, build) | implementer | claude-opus-5-5 | claude-opus-5-5 | medium | medium | 8959225 | 30023 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md; run: docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org; inline: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready: two surviving requirements contradict the retirement | 2 | 1 | 4 | 0 | 3 | 0 |
| Reviewer | retires the pages, but removes lab-used CSS and leaves obsolete staged routes behind | 0 | 2 | 0 | — | 2 | 0 |

## Hand-backs

- 2 Critic: collection-index "Index data" still required the retired field options — delta added (already written before the report arrived).
- 2 Critic: site-build "Deployment under a path prefix" allowed no lab links without `params.lab` — delta names the links into the lab every build writes.
- 2 Critic: "Routes in the lab" dropped the result keys of "Derived routes" — the keys of `route_tree`'s result restated.
- 3 Tests (site, build): removing `FacetIndentTests` lost the only coverage of the facet indent by `--depth` — the sentence added to site-catalogue "Catalogue controls" and the indent test restored inline; the grid-span test stays removed.
- 3 Tests (site, build): the registry problem-format test had no registry error left — accepted.
- 3 Tests (lab): the check for `/compounds/` links is scoped to `main`, the menu coming from `site/hugo.toml` — accepted; the root suite tests the menu.
- 4 Implementation (lab): migration 0003 imported the removed validator — settled in the brief: drop the reference, add no migration.
- 4 Implementation (lab): test docstrings in `webapp/tests/test_collection_routes.py` cited "Derived routes" — reworded inline after the boundary check.
- 4 Implementation (site, build): kept the catalogue script's read of `data-text` because "Catalogue in a browser" still named it — the delta was wrong; fixed the delta and removed the read inline.
- 4 Implementation (site, build): `validate.run` lost its registry parameter, `PROCEDURE_WITHHELD_OPTIONS` kept for the living procedure-fields requirement, `field-value.html` lost its `page` flag, the home entry got its own key `home_substances`, a stale `build/data/routes.json` is not deleted — accepted, then reversed after the review (below).
- 5 Docs: sentences stating that `group` is a valid key, which only the retired reservation explained, removed inline; "The tools keep four built-in registry fields" reworded inline.
- 6 Review: the route tree's and the structure image's rules went from the site's `base.css` while the lab's substance page still uses them — moved to `lab.css` (8d6551f).
- 6 Review: a `build/data/routes.json` from an earlier build survives every rebuild — the build clears `build/data/` before staging; build-script delta and a test added (88ce3ee).

## Test boundary

held
