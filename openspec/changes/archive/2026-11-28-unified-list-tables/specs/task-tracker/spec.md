## ADDED Requirements

### Requirement: Task details
The task list SHALL be a main list (web-app "Main lists") whose details of a task, `/lab/tasks/<number>/detail/`, show:

- the number and the substance's name as heading, linking to the task's page;
- its state as a badge, followed by `Nacharbeit` (`Follow-up`) when the task needs it;
- its priority with its mark, as the task list shows it;
- its assignee and dates;
- its progress as `<done>/<steps>`;
- its product batches, each linking to its page;
- the two flags as `ja` or `nein` (`yes`, `no`);
- its note;
- each field `–` when it has no value;
- its steps, when it has any, in a table with the columns `Stufe`, `Vorschrift` and `Erledigt` (`Step`, `Procedure`, `Done`): the step's position; its procedure's ID linking as the task page links it, followed for a general procedure by `Eintrag <n>`, or empty for a step without an entry; and the date the step was done, or empty;
- a link `Aufgabenseite öffnen` (`Open task page`) to the task's page.

For a signed-in user the details also link `Bearbeiten` (`Edit`) to the task's edit form. The details endpoint answers only GET, other methods with 405, and its path is never read as a task action.

#### Scenario: Details of a task
- **WHEN** the demo collection is imported and a test client requests the task list with `state=all` and `selected` naming a task with the sequence `SEQ-0002` whose first step was done on 2026-11-03
- **THEN** `#item-detail` is headed by the task's number and product, linking to its page, and lists its steps with `OSDB-0004` done on `03.11.2026` and `OSDB-0009` with `Eintrag 1`, each linking to its procedure, and links `Aufgabenseite öffnen`, and no `Bearbeiten` for a visitor

#### Scenario: Details are not an action
- **WHEN** a signed-in user requests `/lab/tasks/<number>/detail/` with `HX-Request: true`, and posts to it
- **THEN** the first answers 200 with the task's `#item-detail`, and the second answers 405 and leaves the task unchanged

## MODIFIED Requirements

### Requirement: Live task list
`/lab/tasks/` SHALL implement live list updates (web-app "Live lists") as a main list (web-app "Main lists"):

- Its filter form (`#filters`) updates `#item-rows` in place with `morph:outerHTML`, each row carrying the stable `id="task-row-<pk>"`. It updates `#task-counts`, `#item-head`, `#item-detail` and `#filter-selected` out of band with `#task-counts:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph`. It uses `hx-get="/lab/tasks/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, and scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`). It keeps its `method="get"`, `action="/lab/tasks/"`, and submit button for no-script use.
- Its column header links update `#item-rows` in place with `hx-sync="#main:replace"`, and out of band `#task-counts:morph,#item-head:morph,#item-detail:morph,#filters:morph`, keeping their `href` fallbacks.
- Its view returns the complete page for plain GET requests and HTMX history restores (`HX-Request: true` with `HX-History-Restore-Request: true`), and varies on `HX-Request` and `HX-History-Restore-Request`. On non-restore HTMX GET responses it sets `HX-Push-Url` to `/lab/tasks/` with cleaned active query parameters:
  - `state`, omitted when `active` (the default) and included otherwise;
  - normalized `person`, `none` or valid uppercase account initials;
  - valid `priority`;
  - trimmed non-empty `q`;
  - `sort` and `dir=desc` as web-app "Main lists" states;
  - the resolved `selected` task number, omitted when the list is empty.
- `/lab/tasks/<number>/detail/` sets `HX-Replace-Url` on HTMX responses to the list URL with the active filters and `selected` naming the task.

#### Scenario: Live filtering and canonical URL on the task list
- **WHEN** a test client requests `/lab/tasks/?state=active&person=kl&priority=bogus&q=+Alpha+`, `/lab/tasks/?state=all&person=none`, `/lab/tasks/?state=running&sort=number`, `/lab/tasks/?state=bogus`, and `/lab/tasks/?q=no-match` with `HX-Request: true`
- **AND** it requests `/lab/tasks/?state=running` once with both `HX-Request: true` and `HX-History-Restore-Request: true`, and once without HTMX headers
- **THEN** all responses return complete page markup (`html`, `#main`, table, filter form) and vary on `HX-Request` and `HX-History-Restore-Request`
- **AND** `#filters` carries `hx-get="/lab/tasks/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`), `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and disjoint `hx-select-oob="#task-counts:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph"`
- **AND** populated `#item-rows` rows carry `id="task-row-<pk>"` and `data-item` with the task's number, the state-filtered response keeps counts across all states in `#task-counts`, and the empty search renders an addressable empty `#item-rows`
- **AND** the five ordinary HTMX responses set `HX-Push-Url` to `/lab/tasks/?person=KL&q=Alpha&selected=<resolved>`, `/lab/tasks/?state=all&person=none&selected=<resolved>`, `/lab/tasks/?state=running&sort=number&selected=<resolved>`, `/lab/tasks/?selected=<resolved>`, and `/lab/tasks/?q=no-match`, while the history-restore and plain GET responses omit `HX-Push-Url`
