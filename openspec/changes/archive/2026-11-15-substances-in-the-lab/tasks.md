## 1. Manifest and import

- [x] 1.1 Tests: the manifest prints each procedure's `status`; the
  demo's stored manifest has it; a missing or unknown status answers
  400 at the manifest and check paths; the lab keeps it, the demo data
  command writes it, and rows without one show no badge
- [x] 1.2 `pipeline.manifest_data` prints `status`; regenerate
  `webapp/demo/manifest.json`
- [x] 1.3 The procedure's `status`, its migration, reading and applying
  it

## 2. Routes in the lab

- [x] 2.1 Tests: the scenarios of "Routes in the lab", and the rules of
  "Derived routes" (order, entries, a step from nothing, depth, budget)
  on the lab's function
- [x] 2.2 `collection/routes.py`: the steps from the rows, one
  substance's tree

## 3. Substance pages and list

- [x] 3.1 Tests: "Procedures beside a substance", "Filters of the
  list", the copy button, sections shown only with items, English texts
- [x] 3.2 The four sections, the copy button and the filters in the
  registry's views and templates; translations

## 4. Verification

- [x] 4.1 In a browser: the pages of `acetylsalicylic-acid`,
  `1-biphenyl-4-yl-ethanol` and `cinnamic-acid`, the filters, the copy
  button
- [ ] 4.2 Run the stack on the test server

## 5. Docs, review and archive

- [x] 5.1 README's substance registry section
- [x] 5.2 Codex reviewer
- [x] 5.3 Archive and squash-merge into `develop`
