## MODIFIED Requirements

### Requirement: Notebooks and entries
The lab application SHALL keep, in its package `journal`, the lab's paper notebooks and the entries that procedures and task steps name; the entries themselves stay on paper:

- a notebook: `code`, as written on its cover, at most 20 characters matching `^[A-Z0-9]+(-[A-Z0-9]+)*$`, such as `AE-2`, unique and fixed once set; `user`, the account whose notebook it is; and `note`, which may be empty. Notebooks keep a change history, and saving or deleting one takes the lock (collection-import "One lock"), since the snapshot lists them (lab-registry "Snapshot").
- an entry: its `notebook` and its `number`, from 1 to 9999, unique within the notebook, written `<code>/<number>`, such as `AE-2/8`. An entry is created when an accepted import (collection-import "Applying an import"), a task step (task-tracker "Task page") or a batch (end-product-inventory "Batches") first names it, and reused whenever one names it again; two of them that name a new entry at once make one entry and both name it. Nothing else creates one.

A notebook that an entry belongs to, an entry that a procedure, task step or batch names, and an account that a notebook belongs to cannot be deleted. Only `demo_data --replace` deletes entries (lab-demo "Demo data command").

#### Scenario: An entry named twice is one entry
- **WHEN** the demo data set is written and the task steps of two tasks are given the journal entry `AE-1/9` one after the other
- **THEN** one entry `AE-1/9` exists, and both steps name it

#### Scenario: A code fixed once set
- **WHEN** a test changes the code of the notebook `AE-1` and saves it
- **THEN** the save raises a validation error and the notebook keeps its code

### Requirement: Journal pages
The journal's pages SHALL need no sign-in:

- `/lab/journal/` lists the notebooks under the heading `Laborjournale` (`Lab notebooks`), ordered by code, in a table with the columns `Journal` (`Notebook`), its code linking to its page; `Inhaber` (`Owner`), the account's initials and display name; `Einträge` (`Entries`), the number of its entries; and `Notiz` (`Note`). For a signed-in user it links `Neues Laborjournal` (`New lab notebook`) to `/lab/journal/new/`.
- `/lab/journal/<code>/` shows the code as heading, the owner and the note, and a table of its entries in order of number with the columns `Eintrag` (`Entry`), written `<code>/<number>`; `Vorschrift` (`Procedure`), the ID of each procedure that names it linking to `/procedures/<ID in lower case>/`, a withdrawn one with the mark `nicht in der Sammlung` and no link; `Aufgabenschritte` (`Task steps`), each task step that names it as its task's number and `Stufe <n>` (`Step <n>`), linking to the task's page; and `Chargen` (`Batches`), each batch that names it, linking to the batch's page, followed by its substance's name. A notebook without entries shows `Keine Einträge.` (`No entries.`). For a signed-in user it links `Bearbeiten` (`Edit`) to `/lab/journal/<code>/edit/`. An unknown code answers 404.

#### Scenario: Notebook list
- **WHEN** the demo data set is written and a test client that is not signed in requests `/lab/journal/`
- **THEN** the table lists `AE-1`, `AE-2`, `CE-1` and `CE-3` in that order, `AE-1` with the owner `KL Katrin Lehmann`, and the page has no link to `/lab/journal/new/`

#### Scenario: Batches of an entry
- **WHEN** two batches, `AE1009FA` and `AE1009FB`, name the entry `AE-1/9`, and a test client requests `/lab/journal/AE-1/`
- **THEN** the row of `AE-1/9` lists both, each linking to its batch's page

#### Scenario: Entries of a notebook
- **WHEN** the demo data set is written and a test client requests `/lab/journal/AE-1/`
- **THEN** the entries are `AE-1/1`, `AE-1/2` and `AE-1/3`, naming `OSDB-0001`, `OSDB-0002` and `OSDB-0003`, each linking to its procedure's page
