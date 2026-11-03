## ADDED Requirements

### Requirement: Derived routes
`pipeline.routes_data(files, depth=6, budget=200)` SHALL return the routes of the compounds that the procedures of `files` make, given `files`, pairs of a path and the front matter of a procedure, a depth limit `depth` and a step budget `budget`. It reads only the front-matter keys `id`, `products`, `substrates` and `scope`. The build calls it with the defaults.

A step to a compound C is a specific procedure of `files` that has C among its `products`, or an entry of a general procedure of `files` that has C among its `products`. The step starts from the compounds of that procedure's or entry's `substrates`, in their order, and from none when `substrates` is unset. The steps to a compound are ordered by procedure ID, the entries of one general procedure in entry order.

A tree of a compound R is built downward from R. Every compound of the tree lies on a path, the compounds from R down to it, both included, and has a level, the number of steps between it and R; R has level 0. The steps a compound of the tree keeps are the steps to it, less every step that starts from a compound on its path, so that a cycle such as a protection followed by its removal is never followed. In the tree of R to the depth `d`, a compound whose level is below `d` is expanded: under it lie the steps it keeps, and under each step the compounds that step starts from, each built by the same rules. A compound whose level is `d` is not expanded; it is cut off when it keeps a step, and a plain leaf when it keeps none. The size of a tree is the number of steps in it, at every level.

The route tree of R is its tree to the largest depth from 1 to `depth` whose size is at most `budget`, or its tree to the depth 1 when even that one is larger. It goes past one step when some step R keeps starts from a compound that is expanded with at least one step, or is cut off.

The result is a table that maps the key of every compound whose route tree goes past one step, and of no other, to the list of the steps R keeps. Each step is a table with these keys and no other:
- `procedure`: the procedure's ID;
- `entry`: only for an entry of a general procedure, its number, counted from 1;
- `yield_percent`: the `yield_percent` of the compound the step makes, in that procedure or entry;
- `substrates`: one table per compound the step starts from, in order, each with the keys `compound`, the compound's key; `steps`, the list of the steps it keeps, built as R's are, when it is expanded, and an empty list otherwise; and `more`, `true` when it is cut off and `false` otherwise.

#### Scenario: Routes of the test collection
- **WHEN** a test calls `routes_data` with the defaults on the procedures that a build of the test collection in locale `en` publishes
- **THEN** its keys are exactly `acetylsalicylic-acid`, `1-biphenyl-4-yl-ethanol` and `cinnamic-acid`
- **AND** `acetylsalicylic-acid` maps to the one step `OSDB-0002` with `yield_percent` 75, which starts from `salicylic-acid`, expanded with the one step `OSDB-0001` at 80 that starts from `methyl-salicylate`, which keeps no step, and from `acetic-anhydride`, which keeps no step, none of them cut off
- **AND** `1-biphenyl-4-yl-ethanol` maps to `OSDB-0005` at 90 and entry 1 of `OSDB-0009` at 90, in that order, each starting from `4-acetylbiphenyl`, expanded with `OSDB-0004` at 85

#### Scenario: A protection and its removal
- **WHEN** a test calls `routes_data` with the defaults on three specific procedures: `OSDB-0001` making `b` from `a`, `OSDB-0002` making `a` from `b`, and `OSDB-0003` making `c` from `b`
- **THEN** its only key is `c`, which maps to `OSDB-0003` starting from `b`, expanded with the one step `OSDB-0001`, which starts from `a`, a plain leaf

#### Scenario: The depth limit
- **WHEN** a test calls `routes_data` on four specific procedures, `OSDB-000<n>` making `c<n>` from `c<n-1>` for `n` from 1 to 4, with the depth 2, and again with the depth 1
- **THEN** with the depth 2 its keys are `c2`, `c3` and `c4`; `c4` maps to `OSDB-0004` starting from `c3`, expanded with `OSDB-0003`, which starts from `c2`, cut off with no steps; and `c2` maps to `OSDB-0002` starting from `c1`, expanded with `OSDB-0001`, which starts from `c0`, a plain leaf
- **AND** with the depth 1 its keys are `c2`, `c3` and `c4`, each mapping to its one step, which starts from a compound cut off with no steps

#### Scenario: The step budget
- **WHEN** a test calls `routes_data` with the depth 6 on four specific procedures, `OSDB-0001` making `r` from `a` and `b`, `OSDB-0002` making `a` from `x`, `OSDB-0003` making `b` from `y`, and `OSDB-0004` making `x` from `z`, first with the budget 4, then 3, then 0
- **THEN** with the budget 4 the tree of `r` reaches `z`, a plain leaf under `OSDB-0004`, and nothing in it is cut off
- **AND** with the budget 3 it is the tree to the depth 2: `x` is cut off with no steps and `y` is a plain leaf
- **AND** with the budget 0 it is the tree to the depth 1: `a` is cut off and `b` is cut off, each with no steps

#### Scenario: Order, entries and a step from nothing
- **WHEN** a test calls `routes_data` with the defaults on, in this order: `OSDB-0003` making `t` from `m`; `OSDB-0001`, a general procedure whose entry 1 makes `t` at 60 from `m` and whose entry 2 makes `t` at 50 from `n`; and `OSDB-0002` making `m` with no `substrates`
- **THEN** `t` maps to entry 1 of `OSDB-0001`, entry 2 of `OSDB-0001` and `OSDB-0003`, in that order, the first two with `entry` and the third without
- **AND** under each step that starts from `m`, `m` is expanded with the one step `OSDB-0002`, whose `substrates` is an empty list, and `m` and `n` are not keys

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
- **WHEN** a test builds a copy of the test collection in locale `en` after adding `tests/fixtures/theme/OSDB-0910-aspirin-hydrolysis.md`, a specific procedure that makes `salicylic-acid` from `acetylsalicylic-acid`, and a general procedure `OSDB-0911` of seven entries, entry `n` making `chain-<n>` from `chain-<n-1>`, with registry files for the eight compounds `chain-0` to `chain-7`, and reads the pages of `salicylic-acid`, `acetylsalicylic-acid` and `chain-7`
- **THEN** the page of `salicylic-acid` lists OSDB-0001 and OSDB-0910 under `Made by` and has no `section.compound-routes`, and the route tree of `acetylsalicylic-acid` names OSDB-0002 and OSDB-0001 and not OSDB-0910
- **AND** the route tree of `chain-7` nests six `li.route-step`, for the entries 7 down to 2 of OSDB-0911, and the item of `chain-1` under the innermost holds no `ul` and ends with ` · ` and a `span.route-more` reading `more steps on its page`, the page's only `span.route-more`

#### Scenario: A German route tree
- **WHEN** a test reads the page of `1-biphenyl-4-yl-ethanol` after a build of the test collection in locale `de`
- **THEN** its `section.compound-routes` has the `h2` `Herstellungswege` and the intro `Wege zu dieser Verbindung aus den Vorschriften der Sammlung, jede Stufe mit ihren Ausgangsstoffen.`, and its second `li.route-step` reads ` · Eintrag 1 · 90 % · ` after its link

#### Scenario: The tree style
- **WHEN** a test reads `site/assets/css/base.css`
- **THEN** a rule for `.route-tree` sets `font-family: var(--font-ui)`, and a rule for `.route-tree ul` sets a `border-left` holding `var(--border)`
