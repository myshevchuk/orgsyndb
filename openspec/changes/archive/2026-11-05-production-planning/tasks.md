## 0. Before implementation

- [x] 0.1 `task-tracker` and `end-product-inventory` are archived and
  merged into `develop`; rebase this branch onto it, and turn the
  navigation, task-list, task-page, task-form and item-page
  requirements into MODIFIED deltas where they change archived specs
- [x] 0.2 The owner confirms the default parameters (21 days of
  synthesis rather than 28)

## 1. Tests

- [x] 1.1 Parameters: defaults, ranges, bands, history, `z`
- [x] 1.2 Matching by text and by compound; articles
- [x] 1.3 Demand models: history and order windows, the choice of
  model, `λ` with rising demand, the size distribution, `m` and `v`
  with the Poisson floor, no demand
- [x] 1.4 Runway: quarterly closed form, certainty 0.5, the order
  model's lumpy cases, zero stock, the article's shared bulk,
  unconvertible lots and items
- [x] 1.5 Synthesis time: default until three exist, longest of the
  last three, ties, cancelled tasks left out, remaining time
- [x] 1.6 Slack, latest start, priority bands; article and task slack;
  late tasks; ended and cancelled tasks
- [x] 1.7 Computed and entered priority on the task list, page, order
  and filter; the form's help text
- [x] 1.8 Item forecast: every figure, `grob` marks, yield of a new
  synthesis, delivery rhythm, reversed lines left out, no demand
- [x] 1.9 Planning list: selection by priority or action, `all=1`,
  order, sizes, tasks and late marks, the three actions, the
  prefilled task form, navigation
- [x] 1.10 Bulk from an ended task; links between tasks and lots of
  the same batch and article

## 2. Implementation

- [x] 2.1 `webapp/planning/`: parameters model and admin; the demand
  models, runways and article sharing as pure functions over plain
  values
- [x] 2.2 Planning list, navigation entry
- [x] 2.3 Additions to the task list, task page, new-task form, item
  page, lot page, and the new-lot form's `batch` and `made_on`

## 3. Docs and archive

- [x] 3.1 `README.md`; a help page explaining the forecast in plain
  words
- [x] 3.2 Review, then archive
