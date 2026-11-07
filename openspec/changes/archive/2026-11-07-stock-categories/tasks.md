## 1. Tests

- [x] 1.1 Levels: each of the seven, the precedence, dormant by
  hand whatever the stock, dormant by the two calendar years, no
  coverage for dormant and never-delivered items
- [x] 1.2 Projected means: the scenario's figures, the floor of one
  quarter, the mark, the switch to complete years; no entered value
  for a quarter to come
- [x] 1.3 Stock entry date: set by the first movement that leaves
  containers, kept afterwards, edited in the form and the admin, not
  after today; recorded in the history
- [x] 1.4 The mark `neu`: this year's entry, last year's, none
- [x] 1.5 Item list: number-only stock cells with title and hidden
  label, the legend's entries, counts and links, `stock=<level>`,
  `sort=urgency` with the new levels
- [x] 1.6 Item page and edit form: level, state, stock entry date
- [x] 1.7 Planning: dormant and never-delivered items without demand,
  their article's figures and bulk unit without them
- [x] 1.8 Colours: contrast of every level token in both schemes
- [x] 1.9 Lab demo: every level on each seeding day, the mark, the
  planning list's required articles, priorities, tasks and actions

## 2. Implementation

- [x] 2.1 `Item.status` and `Item.stocked_on`, with a migration
- [x] 2.2 Bookings: set `stocked_on` in `_movement`
- [x] 2.3 Figures: levels, projection, coverage
- [x] 2.4 Views, templates, forms, admin, `lab.css`, translations
- [x] 2.5 Planning: no demand for dormant and never-delivered items
- [x] 2.6 Demo data

## 3. Docs and archive

- [x] 3.1 `README.md`: stock categories, the state, the mark, the
  projection
- [x] 3.2 `openspec/STATE.md`: the second-year mean; handling
  discontinued items
- [x] 3.3 Review, then archive
