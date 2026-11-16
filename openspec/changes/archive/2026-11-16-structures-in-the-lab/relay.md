# Relay record: structures-in-the-lab

| Stage | Agent | Model requested | Model recorded | Effort requested | Effort recorded | Input tokens | Output tokens | Outcome |
|---|---|---|---|---|---|---|---|---|
| 1 Proposal | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done |
| 2 Critic | codex critic | gpt-6-astra | not read | high | not read | not read | not read | aborted: Codex usage limit, no report |
| 2 Critic | codex critic | gpt-6-astra | not read | medium (operator's override of the pinned high) | not read | not read | not read | run |
| 3 Tests (lab) | test-writer | sonnet | claude-sonnet-5-5 | high | high | 3671917 | 53228 | done |
| 3 Tests (build, deployment, Emacs) | test-writer | sonnet | claude-sonnet-5-5 | high | high | 15839593 | 98402 | done |
| 4 Implementation (demo data) | orchestrator, inline | claude-opus-5-5 | — | session | — | not separable | not separable | done: tasks 1.5 and 2.2, shared by both implementers |
| 4 Implementation (lab) | implementer | opus | claude-opus-5-5 | medium | medium | 4969801 | 33016 | done |
| 4 Implementation (build, deployment, Emacs) | implementer | opus | claude-opus-5-5 | medium | medium | 4363800 | 22954 | done |
| 5 Docs | codex doc writer | gpt-6.1-sol | not read | high | not read | not read | not read | run: README.md, docs/SCHEMA.md, docs/SCHEMA.de.md, docs/AUTHORING.md, docs/AUTHORING.de.md, docs/AUTHORING-ORG.org, docs/AUTHORING-ORG.de.org; inline: line wrapping in README.md, docs/AUTHORING.md, docs/AUTHORING-ORG.org, and README.md's NUL rule after review |
| 6 Review | codex reviewer | gpt-6.1-sol | not read | xhigh | not read | not read | not read | run |

| Gate | Verdict | Blocking | Worth fixing | Noted | Unverified | Accepted | Rejected |
|---|---|---|---|---|---|---|---|
| Critic | not ready — deployment cannot fetch the proposed images, and the history contract needs an explicit exception | 2 | 1 | 3 | 1 | 3 | 0 |
| Reviewer | scenarios implemented; two reproduced input-validation gaps | 0 | 2 | 0 | — | 2 | 0 |

## Hand-backs

- Critic: the deployment builds from the snapshot it pins in a file, so
  the build would find no images — accepted; container-deployment
  "Update cycle" fetches the images beside the kept snapshot.
- Critic: the cached drawing left out of the history contradicted
  web-app "Change history" — accepted; web-app delta added.
- Critic: `keep_registry_inside` copied the demo registry without its
  images — accepted; task 2.5 extended.
- Critic (noted): Hugo gives the collection's static mount precedence
  over the staged images — recorded as a risk in design.md.
- Stage 3 (build): `orgsyndb index` reads `structure_image` from the
  images the last build staged — accepted, as collection-index's
  "values as the build stages them".
- Stage 4 (lab): a test helper writes atom lines a column short, which
  RDKit reads with atom map number 0 — kept the helper; the drawing
  clears atom map numbers, which a structure drawing never needs.
- Stage 4 (build): edited `tools/orgsyndb`, outside its brief, to call
  the staging — accepted; the build had to call it.
- Reviewer: snapshot keys used as paths in the updater before any key
  check — accepted; the updater's snapshot check takes only keys of the
  substance key pattern, and a test was added.
- Reviewer: a NUL character in a molfile passes the checks and fails
  the PostgreSQL save — accepted; refused at the structure, the
  lab-registry delta names it, and a test was added.

## Test boundary

held: no file the test writers committed in 9aaafe9 and 0f8c507 changed
in stage 4. After review the orchestrator added one test each to
`webapp/tests/test_registry_forms.py` and `tests/test_deploy.py`.
