## MODIFIED Requirements

### Requirement: Routes on compound pages
A compound page SHALL end its `main` with `section.compound-routes` when its compound is a key of the route data the build staged (build-script "build subcommand"), and have none otherwise. The section holds the `h2` `Routes`, a `p.routes-intro` with the text `Ways to make this compound from the collection's procedures, each step with the compounds it starts from.`, and a `ul.route-tree` with one `li.route-step` per step the data lists for the compound, in order.
- A `li.route-step` holds an `a` linking the procedure's page with the text `<ID> <title>`, then, for an entry of a general procedure, ` · entry <n>`, then ` · ` and the step's yield as `<n> %`, then ` · ` and the procedure's status badge, all written as the `Made by` list writes them (site-theme "Compound pages"); then, when the step starts from any compound, a `ul` with one `li.route-compound` per compound it starts from, in order.
- A `li.route-compound` holds the compound's `a.compound` with its note (compound-fields "Values beside compound links"); then, when the compound keeps steps, a `ul` with one `li.route-step` per step, in order; or, when it is cut off, ` · ` and a `span.route-more` with the text `more steps on its page`.

`site/assets/css/base.css` sets `.route-tree` in `var(--font-ui)` and gives each `ul` inside it a left border in `var(--border)`.

#### Scenario: Route trees follow the data
- **WHEN** a test scans every compound page after a theme build in locale `en`
- **THEN** a page has a `section.compound-routes`, the last child of `main`, exactly when its compound is a key of the build's `build/data/routes.json`, and its `ul.route-tree` lists, level by level, the steps and compounds the data gives, each step with its link, entry, yield and badge and each compound with its link and, exactly when the data marks it cut off, its `span.route-more`
- **AND** the pages of `salicylic-acid`, `4-acetylbiphenyl` and `methyl-salicylate` have no `section.compound-routes`

#### Scenario: The route of aspirin
- **WHEN** a test reads the page of `acetylsalicylic-acid` after the same build
- **THEN** its route tree holds one `li.route-step`, whose link reads `OSDB-0002 Aspirin (acetylsalicylic acid)` followed by ` · 75 % · ` and the badge `draft`, and whose `li.route-compound` items link `salicylic-acid` and `acetic-anhydride`, in that order
- **AND** the item of `salicylic-acid` holds one `li.route-step` for `OSDB-0001` with ` · 80 % · `, under which one `li.route-compound` links `methyl-salicylate` and holds no `ul`, and the page has no `span.route-more`

#### Scenario: Two steps to one compound
- **WHEN** a test reads the page of `1-biphenyl-4-yl-ethanol` after the same build
- **THEN** its route tree holds two `li.route-step`, for `OSDB-0005` with ` · 90 % · ` and for `OSDB-0009` with ` · entry 1 · 90 % · `, and under each the item of `4-acetylbiphenyl` holds one `li.route-step` for `OSDB-0004` with ` · 85 % · `

#### Scenario: A cycle and the depth limit on the page
- **WHEN** a test builds a copy of the test collection in locale `en` after adding `tests/fixtures/theme/OSDB-0910-aspirin-hydrolysis.md`, a specific procedure that makes `salicylic-acid` from `acetylsalicylic-acid`, and a general procedure `OSDB-0911` of seven entries, entry `n` making `chain-<n>` from `chain-<n-1>`, with the eight substances `chain-0` to `chain-7` added to the registry of the copy, and reads the pages of `salicylic-acid`, `acetylsalicylic-acid` and `chain-7`
- **THEN** the page of `salicylic-acid` lists OSDB-0001 and OSDB-0910 under `Made by` and has no `section.compound-routes`, and the route tree of `acetylsalicylic-acid` names OSDB-0002 and OSDB-0001 and not OSDB-0910
- **AND** the route tree of `chain-7` nests six `li.route-step`, for the entries 7 down to 2 of OSDB-0911, and the item of `chain-1` under the innermost holds no `ul` and ends with ` · ` and a `span.route-more` reading `more steps on its page`, the page's only `span.route-more`

#### Scenario: A German route tree
- **WHEN** a test reads the page of `1-biphenyl-4-yl-ethanol` after a build of the test collection in locale `de`
- **THEN** its `section.compound-routes` has the `h2` `Herstellungswege` and the intro `Wege zu dieser Verbindung aus den Vorschriften der Sammlung, jede Stufe mit ihren Ausgangsstoffen.`, and its second `li.route-step` reads ` · Eintrag 1 · 90 % · ` after its link

#### Scenario: The tree style
- **WHEN** a test reads `site/assets/css/base.css`
- **THEN** a rule for `.route-tree` sets `font-family: var(--font-ui)`, and a rule for `.route-tree ul` sets a `border-left` holding `var(--border)`
