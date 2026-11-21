## 1. Tests

- [ ] 1.1 Batches: fields per source, fixed fields, made numbers unique
  regardless of case and substance, a bought batch with no number,
  entry, step or yield, display as number, supplier's batch or
  `#<id>`, a step's products only, recording only from a planned or
  running task's step, the step's journal entry taken, deletion
  refused while vessels exist (`test_inventory_batches.py`)
- [ ] 1.2 Vessels: the batch's substance, kinds derived (`Kolben`,
  `Endprodukt`, `Zwischenprodukt`, `Reagenz`), at most one flask per
  batch, opening, correction, withdrawal and its reversal, transfer
  into an existing and into a new vessel, across unit kinds through the
  molar mass, refused without one, into a flask, above the amount
  and when the converted amount rounds to zero; the `transfer_in`
  naming the `transfer_out`; atomic conditional updates; a closed
  task's flask refusing corrections and reversals; a batch made by a
  step not deleted outside the demo reset
  (`test_inventory_vessels.py`, replacing `test_inventory_bulk.py`
  and `test_inventory_withdrawals.py`)
- [ ] 1.3 Filling: a vessel required by the booking and the form, the
  proposal and conversion scenarios with vessels, the vessels offered
  as `<batch> #<id> · <kind> · <location> · <amount>`, reversal
  returning the amount to the vessel, bulk counts over open vessels
  flasks included (`test_inventory_forms.py`,
  `test_inventory_numbers.py`, `test_inventory_detail.py`)
- [ ] 1.4 Batch form: `?step=` fills substance, source, date and the
  step's entry, the amount required and stored as yield, flask without
  a location and a stored vessel with one; without a step an optional
  stored vessel; the errors listed in "Inventory forms"; a new entry
  `<code>/<number>` created on first naming; the edit form; a new
  vessel of a batch (`test_inventory_batch_forms.py`, replacing
  `test_inventory_step_lots.py`)
- [ ] 1.5 Lists and pages: batch list (columns, order, `q`), batch
  page (vessels, fillings, links), vessel list (columns, order,
  `empty=1`, `kind=`), vessel page (movements with transfers, links),
  section tabs `Artikel`, `Chargen`, `Gefäße`, `Lieferungen`; the item
  list's details and the item page naming vessels; the old `/bulk/`
  addresses answer 404 (`test_inventory_pages.py`,
  `test_inventory_lists.py`)
- [ ] 1.6 Tasks: no `batch` field; ending needs a product batch by
  action and by form; `fail` only without one; end, fail and a
  form and admin saves that end, fail or cancel write off flasks with a
  `remainder` dated today, also for a backdated end and for an
  intermediate's flask on failure, the end message naming the amounts;
  a refused save leaving task and flask unchanged; ending refused
  without a step; the steps total refused where it would remove a step
  that made a batch or took a withdrawal; the list's `Charge` column and `q`
  over batch numbers; the page's product batches, per-step batches
  with flask and stored amounts, `Charge erfassen`, no `Als Bulk
  erfassen`; a sequence change refused once a step made a batch; the
  admin's search (`test_task_model.py`, `test_task_actions.py`,
  `test_task_forms.py`, `test_task_list.py`, `test_task_page.py`)
- [ ] 1.7 Planning: runway, planning list actions and starting from
  stock read open vessels; "Batches of tasks" scenarios
  (`test_planning_runway.py`, `test_planning_list.py`,
  `test_planning_stock.py`, `test_planning_batches.py`)
- [ ] 1.8 Journal: a batch creates and holds an entry; the notebook
  page's `Chargen` column (`test_journal_entries.py`,
  `test_journal_pages.py`)
- [ ] 1.9 Registry page `Chargen` section; overview figure
  `Offene Gefäße`; substance links on batch and vessel pages
  (`test_registry_pages.py`, `test_overview.py`,
  `test_substance_links.py`)
- [ ] 1.10 Diagram: boxes `inventory_batch`, `inventory_vessel`,
  `inventory_vesselmovement`, the one declared link, the renamed
  columns (`test_schema_diagram.py`)
- [ ] 1.11 Demo: every filling names a vessel, the item of
  `1-phenylethanol` filled from its task's flask, two batches of one
  entry, a bought batch with supplier fields, a transfer from a flask,
  no flask of a closed task holding an amount, the demo planning
  unchanged on every seeding day (`test_demo_records.py`,
  `test_demo_changes.py`, `test_demo_days.py`); `--replace` deletes
  batches, those without vessels among them (`test_demo_command.py`)
- [ ] 1.12 Existing tests that name lots, bulk addresses or fillings
  without a lot moved to the new rules: `test_shell.py`,
  `test_inventory_movements.py`, `test_inventory_admin.py`, and any
  other the area runs turn up
- [ ] 1.13 Bookings against a closing task: a batch recording, a flask
  booking and a flask correction prepared while the task was open and
  stored after it closed are refused; on PostgreSQL, two connections
  overlapping a booking with a closure, either winning, and an admin
  closure or substance change losing to a batch that committed first,
  with the error at its field; the made-number key folds `ß` (`Straße`
  and `STRASSE` collide), an admin rename frees the old number and
  claims the new key; a task's substance refused once a step made a
  batch, in the form and the admin; the demo reset replacing a flask
  with transfers and a remainder

## 2. Implementation

- [ ] 2.1 Models and generated schema migrations: `Batch` with
  `number_key`, `Vessel`, `VesselMovement`, `Movement.vessel_movement`,
  `Task.batch` dropped, histories
- [ ] 2.2 `inventory.bookings`: batch recording with its first vessel,
  vessel opening, filling with a required vessel, withdrawal,
  transfer, correction, remainder write-off for a task, reversals
- [ ] 2.3 Inventory forms, views, URLs and templates: batch list and
  page, vessel list and page, the forms, section tabs, item list
  details and item page
- [ ] 2.4 Tasks: the end rule, actions and forms calling the
  write-off, list, page (`step_lots.html` becomes the step's batches),
  admin
- [ ] 2.5 Planning, overview, journal and registry views and
  templates
- [ ] 2.6 Admin for batches and vessels
- [ ] 2.7 Demo data and seeding, closing tasks through the write-off
  service, the `1-phenylethanol` task ending after its filling
- [ ] 2.8 `schema_diagram.py` grid and declared links; regenerate
  `webapp/docs/database-schema.html`
- [ ] 2.9 German catalogues of `inventory`, `tasks`, `planning`,
  `overview`, `journal` and `registry`: new strings, obsolete ones
  removed, compiled

## 3. Documentation

- [ ] 3.1 `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`,
  `docs/PLANNING.md` and `docs/PLANNING.de.md`: batches, vessels,
  flasks and transfers in place of bulk lots; tasks without a batch
  field (Codex doc writer)
- [ ] 3.2 Purposes of `end-product-inventory`, `production-planning`
  and `task-tracker` brought in line after archive

## 4. Verification

- [ ] 4.1 Both suites pass on CI
- [ ] 4.2 On the test server after `demo_data --replace`: record a
  batch from a step into the flask, fill containers from it, transfer
  part of the rest into a stored vessel, end the task and see the
  remainder written off; the vessel list's
  kinds; a notebook page's batches

## 5. Review and archive

- [ ] 5.1 Codex reviewer
- [ ] 5.2 Archive and squash-merge into `develop`
