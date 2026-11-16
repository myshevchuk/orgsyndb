## 1. Site

- [x] 1.1 Tests: every `a.compound` links `/lab/registry/substances/<key>/`
  with its note; no page under `/compounds/`; no `nav.section-tabs`
  but the procedure tabs; the home page's `Substances` entry; the menu
  without `Compounds`; the catalogue script without `match` and the
  text-search mode; the declared facets' values and labels; the German
  strings and names; the sequence panel
- [x] 1.2 Remove the compound section, its layouts, partials, content,
  styles and strings, the menu entry, and the compound parts of the
  catalogue scripts; re-point `compound-link.html`; the home page entry

## 2. Build and validator

- [x] 2.1 Tests: no `build/data/routes.json` and no `routes_data`; the
  field data and the index without `column`, `facet`, `search` and
  `tabs`; the staged substance data; a substance keyed `group` passes
  the validator
- [x] 2.2 `tools/pipeline.py` and `tools/orgsyndb`: routes, field
  options; `tools/validate.py`: the reserved key

## 3. Lab

- [x] 3.1 Tests: no link `In der Sammlung`, and a substance keyed
  `group` saved by the form; "Routes in the lab" with the depth limit
- [x] 3.2 `webapp/registry/`: the link, its query and the reserved key

## 4. Verification

- [x] 4.1 In a browser: a procedure page, a general procedure's scope
  table, a sequence page and the home page link the lab's substance
  pages; the catalogue searches and filters
- [ ] 4.2 Run the stack on the test server

## 5. Docs, review and archive

- [x] 5.1 README and the `docs/` guides, in both languages, through the
  doc writer
- [x] 5.2 Codex reviewer
- [x] 5.3 Archive; bring synthesis-routes' Purpose in line;
  squash-merge into `develop`
