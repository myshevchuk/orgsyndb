## MODIFIED Requirements

### Requirement: Front matter of an Org source
`osdb-org-front-matter` SHALL take the text of an Org source and return the front matter its keywords give, without exporting and without loading Org: an alist of (KEY . VALUE) pairs, KEY a symbol, in the order of their lines and, on one line, of their pairs. `#+TITLE` gives `title` and `#+HUGO_SLUG` gives `slug`, each the keyword's trimmed value; `#+HUGO_TAGS` gives `tags`, the list of its space-separated words; and every `:key value` pair of every `#+HUGO_CUSTOM_FRONT_MATTER` line gives `key` with the Lisp value that `read` returns for the value's text, after one leading `'` is removed. A pair whose value cannot be read is left out. Keyword names match in any case, and lines inside blocks are skipped, as `osdb-org-keywords` skips them. When `osdb-org-scope` reads the text's table named `scope` without a problem, the alist ends with `scope`, the list of the entries it returns.

#### Scenario: Demo source
- **WHEN** an ERT test calls `osdb-org-front-matter` on the text of `examples/demo/org/procedures/OSDB-0007-ethyl-cinnamate.org`
- **THEN** `title` is `"Ethyl cinnamate"`, `slug` is `"osdb-0007"`, `tags` is `("sample-data" "wittig" "cinnamate")`, `id` is `"OSDB-0007"`, `authors` is `("aschmidt")`, `working_time` is `5`, `inert_atmosphere` is the symbol `true`, and `products` is `(((compound . "ethyl-cinnamate") (yield_percent . 80)))`
- **AND** the keys come in the order `title`, `slug`, `tags`, `id`, `authors`, `status`, `reaction_types`, `scale`, `notebook`, `project`, `working_time`, `inert_atmosphere`, `substrates`, `hazards`, `references`, `products`

#### Scenario: Scope table
- **WHEN** an ERT test calls `osdb-org-front-matter` on the text of `tests/fixtures/export/OSDB-0909-scope-table.org`
- **THEN** `scope` is the last key and holds three entries, the first with `substrates` `("acetic-acid" "ethanol")` and `products` `(((compound . "ethyl-acetate") (yield_percent . 45.5)) ((compound . "propyl-acetate") (yield_percent . 30)))`

#### Scenario: Blocks and unreadable values
- **WHEN** an ERT test calls `osdb-org-front-matter` on a text holding `#+hugo_custom_front_matter: :status "draft" :scale "5 mmol`, then a `#+begin_example` block holding `#+HUGO_CUSTOM_FRONT_MATTER: :id "OSDB-0001"`
- **THEN** the result is `((status . "draft"))`
