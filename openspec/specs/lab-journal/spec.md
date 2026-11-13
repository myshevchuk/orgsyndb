# lab-journal Specification

## Purpose
Keep the lab's paper notebooks in the lab application, number the entries that procedures and task steps name, and show which procedures and steps each entry holds.
## Requirements
### Requirement: Notebooks and entries
The lab application SHALL keep, in its package `journal`, the lab's paper notebooks and the entries that procedures and task steps name; the entries themselves stay on paper:

- a notebook: `code`, as written on its cover, at most 20 characters matching `^[A-Z0-9]+(-[A-Z0-9]+)*$`, such as `AE-2`, unique and fixed once set; `user`, the account whose notebook it is; and `note`, which may be empty. Notebooks keep a change history, and saving or deleting one takes the lock (collection-import "One lock"), since the snapshot lists them (lab-registry "Snapshot").
- an entry: its `notebook` and its `number`, from 1 to 9999, unique within the notebook, written `<code>/<number>`, such as `AE-2/8`. An entry is created when an accepted import (collection-import "Applying an import") or a task step (task-tracker "Task page") first names it, and reused whenever one names it again; an import and a task step, or two task steps, that name a new entry at once make one entry and both name it. Nothing else creates one.

A notebook that an entry belongs to, an entry that a procedure or task step names, and an account that a notebook belongs to cannot be deleted. Only `demo_data --replace` deletes entries (lab-demo "Demo data command").

#### Scenario: An entry named twice is one entry
- **WHEN** the demo data set is written and the task steps of two tasks are given the journal entry `AE-1/9` one after the other
- **THEN** one entry `AE-1/9` exists, and both steps name it

#### Scenario: A code fixed once set
- **WHEN** a test changes the code of the notebook `AE-1` and saves it
- **THEN** the save raises a validation error and the notebook keeps its code

### Requirement: Journal pages
The journal's pages SHALL need no sign-in:

- `/lab/journal/` lists the notebooks under the heading `Laborjournale` (`Lab notebooks`), ordered by code, in a table with the columns `Journal` (`Notebook`), its code linking to its page; `Inhaber` (`Owner`), the account's initials and display name; `Einträge` (`Entries`), the number of its entries; and `Notiz` (`Note`). For a signed-in user it links `Neues Laborjournal` (`New lab notebook`) to `/lab/journal/new/`.
- `/lab/journal/<code>/` shows the code as heading, the owner and the note, and a table of its entries in order of number with the columns `Eintrag` (`Entry`), written `<code>/<number>`; `Vorschrift` (`Procedure`), the ID of each procedure that names it linking to `/procedures/<ID in lower case>/`, a withdrawn one with the mark `nicht in der Sammlung` and no link; and `Aufgabenschritte` (`Task steps`), each task step that names it as its task's number and `Stufe <n>` (`Step <n>`), linking to the task's page. A notebook without entries shows `Keine Einträge.` (`No entries.`). For a signed-in user it links `Bearbeiten` (`Edit`) to `/lab/journal/<code>/edit/`. An unknown code answers 404.

#### Scenario: Notebook list
- **WHEN** the demo data set is written and a test client that is not signed in requests `/lab/journal/`
- **THEN** the table lists `AE-1`, `AE-2`, `CE-1` and `CE-3` in that order, `AE-1` with the owner `KL Katrin Lehmann`, and the page has no link to `/lab/journal/new/`

#### Scenario: Entries of a notebook
- **WHEN** the demo data set is written and a test client requests `/lab/journal/AE-1/`
- **THEN** the entries are `AE-1/1`, `AE-1/2` and `AE-1/3`, naming `OSDB-0001`, `OSDB-0002` and `OSDB-0003`, each linking to its procedure's page

### Requirement: Journal forms
A signed-in user SHALL register and edit notebooks through these forms, each saved with its change history:

- `/lab/journal/new/`: the code; the owner, a choice of every account shown as initials and display name, the signed-in user's selected; and the note;
- `/lab/journal/<code>/edit/`: the owner and the note, the code shown and not editable.

A code that breaks its pattern or is taken shows an error at its field and saves nothing. A saved form leads to the notebook's page with the message `Laborjournal <code> gespeichert.` (`Lab notebook <code> saved.`).

#### Scenario: Registering a notebook
- **WHEN** user `klehmann` posts the new-notebook form with the code `KL-1` and no owner change
- **THEN** the notebook `KL-1` exists with the owner `klehmann`, its history records its creation, `/lab/journal/KL-1/` opens, and the snapshot's digest differs from the one before

#### Scenario: A bad code
- **WHEN** a signed-in user posts the new-notebook form with the code `KL/1`, and then with the code `AE-1`
- **THEN** each shows an error at the code and no notebook is created

### Requirement: Journal in the admin
The admin SHALL list the notebooks for staff, with search by code, the change history of each, and the code read-only once a notebook exists; and list the entries read-only, with no way to add or change one. A notebook with entries cannot be deleted.

#### Scenario: Entries read-only
- **WHEN** a staff user posts to the admin's add page of a journal entry
- **THEN** the answer is 403 and no entry is created

