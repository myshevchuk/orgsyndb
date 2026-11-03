## ADDED Requirements

### Requirement: Package files
The application SHALL ship the Emacs package `orgsyndb` in its `emacs/` directory. `emacs/orgsyndb.el` provides the feature `orgsyndb` and carries the headers of a package named `orgsyndb`, with `Package-Requires: ((emacs "29.1"))`. The package's other files are `emacs/orgsyndb-<part>.el` and the Org front end `emacs/osdb-org.el` (org-export "Org front-end library"). The package uses only libraries that Emacs 29.1 ships; only `emacs/orgsyndb-flycheck.el` refers to Flycheck, and it does not require it. Loading `orgsyndb` defines functions, modes, variables and options and changes no other state: it turns on no mode and adds to no global hook or list. `global-orgsyndb-mode` and the commands are autoloaded.

#### Scenario: Clean byte compilation
- **WHEN** a test byte-compiles each file under `emacs/` in its own `emacs -Q --batch` with `byte-compile-error-on-warn` set and only `emacs/` added to `load-path`
- **THEN** every compilation succeeds

#### Scenario: Loading changes nothing
- **WHEN** an ERT test records the global values of `before-save-hook`, `after-save-hook`, `completion-at-point-functions`, `xref-backend-functions`, `flymake-diagnostic-functions` and `eldoc-documentation-functions` and the value of `time-stamp-format`, then loads `orgsyndb`
- **THEN** each value is unchanged, `global-orgsyndb-mode` is off, and `org` is not a feature

### Requirement: The program the package calls
The package SHALL run the program named by the user option `orgsyndb-program`. Its default is `<app>/tools/orgsyndb`, where `<app>` is the parent of the directory that holds the true name of the loaded `orgsyndb.el`, when that file exists, and `orgsyndb` otherwise. Every run passes `-C <collection>` before the subcommand, with the collection as `default-directory`.

#### Scenario: Program beside the package
- **WHEN** an ERT test loads the package from the repository's `emacs/` directory
- **THEN** the standard value of `orgsyndb-program` is the absolute file name of the repository's `tools/orgsyndb`

### Requirement: Turning the mode on
`global-orgsyndb-mode` SHALL turn on `orgsyndb-mode`, whatever the major mode, in each buffer visiting a file whose kind is not nil. `orgsyndb-collection-root` returns the collection of a file, the nearest directory at or above the file's directory that holds `orgsyndb.toml`, or nil. `orgsyndb-file-kind` returns the kind of a file from its path relative to its collection:
- `org-procedure` for a `.org` file directly in `org/procedures/`;
- `md-procedure` for a `.md` file directly in `md/procedures/`;
- `sequence` for a `.md` file directly in `md/sequences/`;
- `compound` for a `.toml` file directly in `compounds/`;
- `vocabulary` for a `.toml` file directly in `vocabularies/`;
- `settings` for `orgsyndb.toml`;
- nil for every other file, and for a file outside any collection.

The mode's lighter is ` OSDB`. The features of the following requirements act only in buffers whose kind they name.

#### Scenario: Kinds
- **WHEN** an ERT test calls `orgsyndb-file-kind` on these files of a copy of the demo collection: `org/procedures/OSDB-0007-ethyl-cinnamate.de.org`, `md/procedures/OSDB-0002-aspirin.md`, `md/sequences/SEQ-0001-aspirin-from-wintergreen.md`, `compounds/acetone.toml`, `vocabularies/projects.toml`, `orgsyndb.toml`, `build/export/OSDB-0007-ethyl-cinnamate.md` and `static/structures/isopentyl-acetate.svg`
- **THEN** it returns `org-procedure`, `md-procedure`, `sequence`, `compound`, `vocabulary`, `settings`, nil and nil

#### Scenario: Turned on by visiting
- **WHEN** an ERT test turns on `global-orgsyndb-mode` and visits `md/procedures/OSDB-0002-aspirin.md` of a copy of the demo collection and a `.md` file in a temporary directory outside any collection
- **THEN** `orgsyndb-mode` is on in the first buffer and off in the second

### Requirement: Collection data
The package SHALL keep, per collection, the index that `orgsyndb index` prints (collection-index "Index data"), parsed with JSON objects as alists keyed by symbols, arrays as lists, `null` as nil and `false` as `:false`. `orgsyndb-index` returns the index of the current buffer's collection, running the program synchronously when the package holds none for it yet. After a buffer in `orgsyndb-mode` is saved, the package runs the program in the background and replaces the collection's index when the run succeeds. A run that exits non-zero leaves the index unchanged and shows the program's error output in a message. `orgsyndb-refresh-index` runs it again for the current collection.

`orgsyndb-procedures` returns one record per entry of the index's `procedures`: the entry, with the `front_matter` of an Org source taken from `osdb-org-front-matter` (org-export "Front matter of an Org source") of the visiting buffer's text when a buffer visits the file, and of the file otherwise, read again when the file's modification time changes.

#### Scenario: First use
- **WHEN** an ERT test calls `orgsyndb-index` in a buffer visiting a file of a copy of the test collection
- **THEN** it returns the parsed index, whose `compounds` holds 20 entries

#### Scenario: Refresh after a save
- **WHEN** an ERT test fetches the index of a copy of the test collection, then creates `compounds/ethanol.toml` through a buffer in `orgsyndb-mode`, saves it and waits for the background run to finish
- **THEN** the index lists the compound `ethanol`

#### Scenario: A new Org source after a save
- **WHEN** an ERT test fetches the index of a copy of the demo collection, then creates `org/procedures/OSDB-0010-test.org` through a buffer in `orgsyndb-mode`, saves it and waits for the background run to finish
- **THEN** `orgsyndb-procedures` holds a record whose `path` is `org/procedures/OSDB-0010-test.org`

#### Scenario: A failed run keeps the index
- **WHEN** an ERT test fetches the index of a copy of the test collection, then sets `orgsyndb-program` to a script that writes `boom` to stderr and exits 1, and calls `orgsyndb-refresh-index`
- **THEN** `orgsyndb-index` returns the earlier index, and the last message contains `boom`

#### Scenario: Org records
- **WHEN** an ERT test calls `orgsyndb-procedures` for a copy of the demo collection
- **THEN** the record of `org/procedures/OSDB-0007-ethyl-cinnamate.org` has the front-matter `title` `Ethyl cinnamate` and `status` `draft`

### Requirement: Completion in Markdown procedures
The mode SHALL put `orgsyndb-completion-at-point` on the buffer's `completion-at-point-functions`. In a buffer of kind `md-procedure`, it offers completions only inside the `+++` front matter:
- At the start of a line, while point follows nothing but the letters, digits and underscores of a key: the schema's top-level procedure keys and the declared procedure field keys that the front matter does not set yet, each annotated `required` when the schema requires it, or with its label when it is a declared field.
- Inside a double-quoted string that is the value, or an entry of the array value, of a key, the values of that key. The key is the innermost one whose value encloses the string, so that `compound` inside a `products` table and `substrates` inside a `scope` entry count as themselves:
  - `status`: the statuses; `language`: the languages;
  - `reaction_types`: the collection's reaction types, annotated with their labels;
  - `tags`: the tags that the collection's procedures use; `authors` and `checked_by`: the names that the procedures use under either key;
  - `substrates` and `compound`: the registry's compound keys, annotated with name and formula;
  - `scheme_image`: `structures/<name>` for each `.svg` or `.png` file directly in the collection's `static/structures/`;
  - a declared `choice` field: the values of its vocabulary, annotated with the labels of the value's ancestors and its own, outermost first, joined by ` › `.
- After `<key> = ` for a declared `boolean` field: `true` and `false`.

Elsewhere, and in the body, it returns nil, so that other completion functions run. Tags and names in use come from the index for Markdown procedures and from `orgsyndb-procedures` for Org sources.

#### Scenario: Status
- **WHEN** an ERT test, in a buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, puts point after `d` in `status = "d"` and calls `orgsyndb-completion-at-point`
- **THEN** the completions of its table for the text before point are `("draft")`

#### Scenario: Reaction type
- **WHEN** the test does the same inside `reaction_types = ["est"]`
- **THEN** the completions are `("esterification")`, annotated with text containing `Esterification`

#### Scenario: Compound of a product
- **WHEN** the test does the same inside `products = [{ compound = "acetyls", yield_percent = 75 }]`
- **THEN** the completions are `("acetylsalicylic-acid")`, annotated with text containing `Acetylsalicylic acid`

#### Scenario: Declared choice
- **WHEN** the test does the same inside `project = "first"`
- **THEN** the completions are `("first-year-practical")`, annotated with text containing `Teaching › First-year practical`

#### Scenario: Keys not yet set
- **WHEN** the test inserts a new line `sc` before the closing `+++` and calls the function with point after `sc`
- **THEN** the completions are `scheme_image` and `scope`, and not `scale`, which the file sets

#### Scenario: Nothing in the body
- **WHEN** the test calls the function with point in the text of the Summary section
- **THEN** it returns nil

### Requirement: Completion in Org procedures
In a buffer of kind `org-procedure`, `orgsyndb-completion-at-point` SHALL offer:
- On a `#+HUGO_CUSTOM_FRONT_MATTER:` line, at a `:` that begins a key: `:id`, and the schema's top-level procedure keys other than `title`, `slug`, `tags`, `date`, `lastmod`, `ai_model` and `scope`, and the declared procedure field keys, each with its leading colon, leaving out those the file's custom front matter sets already.
- Inside a double-quoted string that is the value, or an entry of the list value, of a `:key` on such a line, the values that "Completion in Markdown procedures" gives for the key; inside the strings of `:products '(((compound . "…`, the compound keys.
- After a declared boolean `:key` and a space: `true` and `false`.
- On a `#+HUGO_TAGS:` line, for the word at point: the tags in use.
- In a cell of the `substrates` or `products` column of the table named `scope`, for the word at point: the compound keys.

Elsewhere it returns nil.

#### Scenario: Custom front-matter keys
- **WHEN** an ERT test writes into a copy of the demo collection an Org source `org/procedures/OSDB-0010-test.org` whose header holds `#+HUGO_CUSTOM_FRONT_MATTER: :status "draft"` and a further line `#+HUGO_CUSTOM_FRONT_MATTER: :s`, visits it and calls `orgsyndb-completion-at-point` with point after `:s`
- **THEN** the completions include `:scale`, `:substrates` and `:scheme_image`, and include neither `:status` nor `:scope`

#### Scenario: Reaction type in a list
- **WHEN** the test does the same inside `:reaction_types '("ol")`
- **THEN** the completions are `("olefination")`

#### Scenario: Product compound
- **WHEN** the test does the same inside `:products '(((compound . "ethyl-c") (yield_percent . 80)))`
- **THEN** the completions are `("ethyl-cinnamate")`

#### Scenario: Tags
- **WHEN** the test does the same after `wit` on the line `#+HUGO_TAGS: sample-data wit`
- **THEN** the completions are `("wittig")`

#### Scenario: Scope table cell
- **WHEN** the test adds `#+NAME: scope` and a table with the header `| substrates | products | yield_percent |`, a separator line and the row `| aceto | | |`, and calls the function with point after `aceto`
- **THEN** the completions are `("acetone" "acetophenone")`

### Requirement: Completion in sequences and compound files
`orgsyndb-completion-at-point` SHALL offer:
- In a buffer of kind `sequence`, inside the front matter: at the start of a line, the sequence keys that the front matter does not set yet; inside the string of `target`, the compound keys; inside the string of `procedure` in a step, the procedure IDs, each annotated with its title; after `entry = ` in a step, the entry numbers `1` to `n` of the general procedure that the step's `procedure` names, each annotated with the compound keys of that entry's products, and nothing when the step names a specific procedure.
- In a buffer of kind `compound`: at the start of a line, the built-in compound keys and the declared compound field keys that the file does not set yet; inside the string value, or an array entry, of a declared choice field, its vocabulary's values, annotated as for procedures; after a declared boolean key, `true` and `false`; inside the string of `structure_image`, the structure images as for `scheme_image`.

#### Scenario: Step procedure
- **WHEN** an ERT test, in a buffer visiting `md/sequences/SEQ-0001-aspirin-from-wintergreen.md` of a copy of the demo collection, calls `orgsyndb-completion-at-point` with point after `OSDB-000` inside `steps = [{ procedure = "OSDB-000" }]`
- **THEN** the completions are the nine IDs `OSDB-0001` to `OSDB-0009`, and `OSDB-0007` is annotated with text containing `Ethyl cinnamate`

#### Scenario: Step entry
- **WHEN** the test does the same with point after `entry = ` in `{ procedure = "OSDB-0009", entry = }`
- **THEN** the completions are `("1" "2" "3")`, and `1` is annotated with text containing `1-biphenyl-4-yl-ethanol`

#### Scenario: Step entry of an Org general procedure
- **WHEN** an ERT test copies `tests/fixtures/export/OSDB-0909-scope-table.org` into `org/procedures/` of a copy of the demo collection and does the same in `{ procedure = "OSDB-0909", entry = }`
- **THEN** the completions are `("1" "2" "3")`, and `1` is annotated with text containing `ethyl-acetate` and `propyl-acetate`

#### Scenario: Compound file
- **WHEN** an ERT test creates `compounds/test.toml` in a copy of the demo collection holding `name = "Test"`, a line `chem` and a line `group = "fin"`, and calls the function after `chem` and after `fin`
- **THEN** the first completions are `("chemical_class")`, and the second are `("final-products")`

### Requirement: Inserting a compound by name
`orgsyndb-insert-compound` SHALL read a compound with completion over one candidate per registry compound, `<name> (<key>)`, using `name_de` when the buffer's file has the language code `de` and the compound has one, annotated with the formula, and insert the chosen compound's key at point.

#### Scenario: Insert by name
- **WHEN** an ERT test, in a buffer visiting `md/procedures/OSDB-0002-aspirin.de.md` of a copy of the test collection, calls `orgsyndb-insert-compound` with the minibuffer input `Essigsäureanhydrid (acetic-anhydride)`
- **THEN** `acetic-anhydride` is inserted at point

### Requirement: Definitions and references
The mode SHALL put an `xref` backend on the buffer's `xref-backend-functions`. Its identifier at point is, anywhere in the buffer, including Org and Markdown body text: a maximal run of lowercase letters, digits and hyphens that is a registry compound key; a procedure ID `OSDB-NNNN`; or a sequence ID `SEQ-NNNN`.
- A compound key's definition is line 1 of its compound file.
- An ID's definition is one file of that ID among the procedures or sequences: the file whose language code is the current file's code, else the file without a code, else the first file in name order.
- A compound key's references are the lines of the collection's procedure and sequence files that contain the key with no lowercase letter, digit or hyphen directly before or after it. An ID's references are the lines of those files that contain the ID.
- The identifiers offered for completion are the compound keys and the IDs.

#### Scenario: Compound definition
- **WHEN** an ERT test, in a buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, asks the backend for the definitions of the identifier at point with point on `acetic-anhydride` in `substrates`
- **THEN** there is one definition, at line 1 of `compounds/acetic-anhydride.toml`

#### Scenario: Procedure definition in the reader's language
- **WHEN** an ERT test asks for the definitions of `OSDB-0001` at point in `md/sequences/SEQ-0001-aspirin-from-wintergreen.md`, and in `md/sequences/SEQ-0001-aspirin-from-wintergreen.de.md`, of a copy of the demo collection
- **THEN** the definitions are `org/procedures/OSDB-0001-salicylic-acid.org` and `org/procedures/OSDB-0001-salicylic-acid.de.org`, one each

#### Scenario: Compound references
- **WHEN** an ERT test asks for the references of `acetic-anhydride` in a copy of the test collection
- **THEN** they include a line of `md/procedures/OSDB-0002-aspirin.md` and one of `md/procedures/OSDB-0002-aspirin.de.md`, and none of `compounds/acetic-anhydride.toml`

### Requirement: Documentation at point
The mode SHALL put a function on the buffer's `eldoc-documentation-functions` that, for the identifier of "Definitions and references" at point, gives one line: for a compound key, `<key>: <name> · <formula> · <mw> g/mol`, followed by ` · CAS <cas>` when the compound sets it; for a procedure ID, `<ID> <title> · <status>`, from the file that is its definition; for a sequence ID, `<ID> <title>`. A part whose value the data lacks is left out with its separator. Elsewhere it gives nothing.

#### Scenario: Compound at point
- **WHEN** an ERT test calls the function with point on `acetic-anhydride` in a buffer of a copy of the test collection
- **THEN** the line is `acetic-anhydride: Acetic anhydride · C4H6O3 · 102.09 g/mol · CAS 108-24-7`

#### Scenario: Procedure at point
- **WHEN** an ERT test calls the function with point on `OSDB-0004` in `md/sequences/SEQ-0002-biphenylyl-ethanol.md` of a copy of the demo collection
- **THEN** the line is `OSDB-0004 4-Acetylbiphenyl · draft`

### Requirement: Language variants
`orgsyndb-visit-variant` SHALL visit another file with the current procedure's or sequence's ID, reading which with completion when there are several, and report when there is none. `orgsyndb-create-translation` SHALL create the file `<base name>.<code>.<suffix>` beside the current procedure, where `<code>` is the language other than the current file's, and visit it. The current file's language is its file-name code, else its `language` value, else `de` when its body headings include more German than English section names and `en` otherwise. The new file holds:
- the current file's front matter, or in Org its lines before the first heading, with `date` and `lastmod`, or `#+CREATED` and `#+LAST_MODIFIED`, set to the current Europe/Berlin time in their exact forms, and `language` set to `<code>` where the current file sets it; every other value unchanged;
- the current file's body, with each section heading of the current language replaced by the heading at the same position in the other language's list.

When the file exists already, the command signals a user error naming it and writes nothing.

#### Scenario: Org translation
- **WHEN** an ERT test removes `org/procedures/OSDB-0007-ethyl-cinnamate.de.org` from a copy of the demo collection, fixes the current time at 2026-07-15T10:00:00Z, and calls `orgsyndb-create-translation` in a buffer visiting `OSDB-0007-ethyl-cinnamate.org`
- **THEN** `org/procedures/OSDB-0007-ethyl-cinnamate.de.org` exists, its `#+HUGO_CUSTOM_FRONT_MATTER` lines equal the source's, its `#+CREATED` and `#+LAST_MODIFIED` are both `[2026-07-15 Wed 12:00:00]`, its top-level headings are the eight German section names in order, the text under its first heading equals the text under the source's `* Summary`, and `osdb-org-lint` of its text reports no problem

#### Scenario: Markdown translation
- **WHEN** an ERT test removes `md/procedures/OSDB-0002-aspirin.de.md` from a copy of the test collection, fixes the current time at 2026-01-15T10:00:00Z, and calls the command in a buffer visiting `OSDB-0002-aspirin.md`
- **THEN** `md/procedures/OSDB-0002-aspirin.de.md` exists, its `date` and `lastmod` are `2026-01-15T11:00:00+01:00`, its level-2 headings are the eight German section names in order, and its other front-matter lines equal the source's

#### Scenario: Existing translation
- **WHEN** an ERT test calls the command in a buffer visiting `org/procedures/OSDB-0007-ethyl-cinnamate.org` of an unchanged copy of the demo collection
- **THEN** it signals a user error naming `OSDB-0007-ethyl-cinnamate.de.org`, and that file is unchanged

#### Scenario: Visit the other variant
- **WHEN** an ERT test calls `orgsyndb-visit-variant` in a buffer visiting `org/procedures/OSDB-0007-ethyl-cinnamate.org` of a copy of the demo collection
- **THEN** the current buffer visits `org/procedures/OSDB-0007-ethyl-cinnamate.de.org`

### Requirement: Problem locations
`orgsyndb-problem-location` SHALL take a collection directory, a problem's path relative to it, the problem's field and its message, and return the file and the line, counting from 1, where the problem belongs:
- The file is the path, except that `build/export/<stem>.md` maps to `org/procedures/<stem>.org`.
- The key is the field up to its first `[` or `.`.
- A `front_matter` or `toml` problem whose message holds `at line <n>` belongs on line `<n>` of the file, the line that `tomllib` names.
- In a Markdown or TOML file, the line is the first line of the front matter, or of the TOML file, that begins, after optional blanks, with the key, bare or in double quotes, followed by optional blanks and `=`, or that is a table header whose first dotted part is the key, such as `[[products]]`.
- In an Org file, the line is the first line of the keyword that writes the key: `#+TITLE` for `title`, `#+HUGO_SLUG` for `slug`, `#+HUGO_TAGS` for `tags`, `#+CREATED` for `date`, `#+LAST_MODIFIED` for `lastmod`, `#+AI_MODEL` for `ai_model`, the keyword itself for a field that begins with `#+`; the `#+NAME: scope` line for `scope`; otherwise the first `#+HUGO_CUSTOM_FRONT_MATTER` line holding `:<key>` followed by a blank or the line's end. Keyword names match in any case.
- The line is 1 when nothing matches.

#### Scenario: Export problem on the Org source
- **WHEN** an ERT test calls `orgsyndb-problem-location` for a copy of the demo collection with the path `build/export/OSDB-0007-ethyl-cinnamate.md`, the message `must be a number`, and the fields `products[1].yield_percent`, `working_time`, `title` and `file_name`
- **THEN** each result names `org/procedures/OSDB-0007-ethyl-cinnamate.org`, with the lines 18, 13, 1 and 1

#### Scenario: Markdown and compound fields
- **WHEN** an ERT test calls it for a copy of the test collection with `md/procedures/OSDB-0002-aspirin.md` and `status`, and with `compounds/acetic-anhydride.toml` and `mw`, each with the message `unknown`
- **THEN** the lines are 8 and 4

#### Scenario: Line of a TOML error
- **WHEN** an ERT test calls it for a copy of the test collection with `compounds/acetic-anhydride.toml`, the field `toml` and the message `invalid TOML: Invalid value (at line 3, column 8)`
- **THEN** the line is 3

### Requirement: Diagnostics of an Org source while typing
In a buffer of kind `org-procedure`, the mode's Flymake backend `orgsyndb-flymake` SHALL report, on each Flymake check, the problems that `osdb-org-check-file-name` gives for the file name and that `osdb-org-lint` and `osdb-org-scope` give for the buffer text, each as a diagnostic of the problem's severity with the text `<field>: <message>`, on the whole line that "Problem locations" gives for the problem's field in the buffer.

#### Scenario: Wrong weekday
- **WHEN** an ERT test visits a copy of `tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org` placed in `org/procedures/` of a copy of the demo collection and runs the backend
- **THEN** it reports one error, on line 2, whose text begins `#+CREATED: weekday "Tue" does not match`

### Requirement: Validation on save
While `orgsyndb-validate-on-save` is non-nil, the default, the package SHALL run `orgsyndb validate` for the collection in the background after a buffer in `orgsyndb-mode` is saved, as "One command at a time" orders the runs. From a run's standard output it reads the problem lines `<path>:<field>: <severity>: <message>`: those whose path lies in `org/procedures/` are export problems, the others validator problems. A run is complete when its standard error holds the validator's summary line `validated <n> files: …`. A complete run replaces the export and validator problems the package keeps for every file of the collection. An incomplete run, one that stopped at the Org export or before it, replaces the export problems only, and shows in the echo area its first problem line of severity `error`, or else the last line of its standard error. `orgsyndb-flymake` reports in each buffer the kept problems of its file, placed by "Problem locations", with the text `<field>: <message>`, beside the diagnostics of "Diagnostics of an Org source while typing"; an export problem with the field, severity and message of one of those is left out.

#### Scenario: Markdown problem after a save
- **WHEN** an ERT test, in a buffer with Flymake visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, changes `status = "draft"` to `status = "done"`, saves, and waits for the run to finish
- **THEN** the buffer has an error diagnostic on line 8 whose text begins `status:`

#### Scenario: Export problem shown on the Org source
- **WHEN** an ERT test, with ox-hugo cached and in a buffer with Flymake visiting `org/procedures/OSDB-0007-ethyl-cinnamate.org` of a copy of the demo collection, changes `:working_time 5` to `:working_time "five"`, saves, and waits for the run to finish
- **THEN** the buffer has an error diagnostic on line 13 whose text begins `working_time:`

#### Scenario: A run stopped by the export keeps earlier problems
- **WHEN** after the first scenario's diagnostic the test creates the directory `org/procedures/nested/` in the collection, saves the Markdown buffer again, and waits for the run to finish
- **THEN** the Markdown buffer still has its `status:` diagnostic, and the last message contains `subdirectories`

#### Scenario: No second copy of a problem shown while typing
- **WHEN** an ERT test, in a buffer with Flymake visiting a copy of `tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org` placed in `org/procedures/` of a copy of the demo collection, saves and waits for the run to finish
- **THEN** the buffer has exactly one diagnostic whose text begins `#+CREATED: weekday`

### Requirement: One command at a time
The package SHALL run, per collection, at most one of the program's commands that write the collection's `build/`, `public/` or `pdf/`: `validate`, `build`, `pdf`, and `serve` until it prints its `serving` line. A command requested while another of them runs starts when that one ends, in the order requested; a `validate` or `build` that is already waiting is not added a second time. `orgsyndb-validate` waits in the same order. A command's turn ends when its process ends, however it ends. `index` and `new` start at once.

#### Scenario: A killed validation buffer gives up its turn
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that sleeps for `validate` and creates `pdf/OSDB-0002-aspirin.pdf` for `pdf`, calls `orgsyndb-validate` in a buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, kills the validation buffer, and calls `orgsyndb-pdf`
- **THEN** a buffer visits `pdf/OSDB-0002-aspirin.pdf`

#### Scenario: A preview build waits for the validation
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that records when each run starts and ends, prints its `serving` line for `serve`, and takes one second for `validate`; starts the server, saves a procedure buffer twice in a row and calls `orgsyndb-preview` while the validation runs
- **THEN** the stub's record shows no two runs other than `serve` overlapping, two runs of `validate`, and the `build` starting after the first `validate` ended

### Requirement: Validation buffer
`orgsyndb-validate` SHALL run `orgsyndb validate` for the current collection in a compilation buffer in which each problem line is an error or a warning by its severity, and `next-error` visits the file and line that "Problem locations" gives for it.

#### Scenario: Next error
- **WHEN** an ERT test changes `status = "draft"` to `status = "done"` in `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, runs `orgsyndb-validate`, waits for it to finish and calls `next-error`
- **THEN** the selected buffer visits `md/procedures/OSDB-0002-aspirin.de.md`, whose problem, that its status differs from its variant's, is the first line of the output, with point on line 8

### Requirement: Diagnostics front end
The user option `orgsyndb-diagnostics` SHALL choose how a buffer of kind `org-procedure`, `md-procedure`, `sequence` or `compound` shows the diagnostics: `flymake`, the default, turns on `flymake-mode` with `orgsyndb-flymake` on the buffer's `flymake-diagnostic-functions`; `flycheck` turns on `flycheck-mode` with the checker `orgsyndb`; nil turns on neither. `emacs/orgsyndb-flycheck.el` defines the checker `orgsyndb` once the feature `flycheck` is present, and not before: a generic checker for buffers in `orgsyndb-mode` that reports the diagnostics `orgsyndb-flymake` would report, with the same lines, severities and texts.

#### Scenario: Flymake by default
- **WHEN** an ERT test visits `org/procedures/OSDB-0007-ethyl-cinnamate.org` of a copy of the demo collection with `global-orgsyndb-mode` on
- **THEN** `flymake-mode` is on, and `flymake-diagnostic-functions` holds `orgsyndb-flymake`

#### Scenario: Checker defined when Flycheck loads
- **WHEN** an ERT test loads `orgsyndb-flycheck`, and then provides a stub feature `flycheck` whose `flycheck-define-generic-checker` records its arguments
- **THEN** nothing was recorded before the stub was provided, and afterwards a checker named `orgsyndb` was recorded whose start function, called in the buffer of "Wrong weekday", reports one error on line 2

### Requirement: Timestamps on save
While `orgsyndb-update-timestamps` is non-nil, the default, the mode SHALL keep the modification time of a procedure or sequence current with `time-stamp`, which a function on the buffer's `before-save-hook` runs after giving `time-stamp-active`, `time-stamp-pattern`, `time-stamp-start`, `time-stamp-end`, `time-stamp-format`, `time-stamp-time-zone`, `time-stamp-line-limit` and `system-time-locale` buffer-local values, `time-stamp-pattern` nil:
- In a buffer of kind `org-procedure`, `time-stamp` rewrites the timestamp of the first `#+LAST_MODIFIED` keyword before the first heading, in any case, as `[YYYY-MM-DD Day hh:mm:ss]`, the Europe/Berlin local time with the English weekday.
- In a buffer of kind `md-procedure` or `sequence`, it rewrites the value of the front matter's `lastmod` key as `YYYY-MM-DDThh:mm:ss+HH:MM`, the Europe/Berlin local time and the offset in force, both from one offset, so that the text names the instant of the save.

The option is read at each save. The global values of those variables are untouched, and turning the mode off gives back each of them, and the buffer's `before-save-hook`, the local value it had before. A file without the keyword or key, before the first heading or in the front matter, is saved unchanged.

#### Scenario: Org in winter
- **WHEN** an ERT test, with the current time fixed at 2026-01-15T10:00:00Z and the global `system-time-locale` set to `de_DE.UTF-8`, saves a modified buffer visiting an Org procedure of a copy of the demo collection whose `#+LAST_MODIFIED` is `[2026-10-20 Tue 10:22:50]`
- **THEN** the saved line is `#+LAST_MODIFIED: [2026-01-15 Thu 11:00:00]`

#### Scenario: Markdown in summer and winter
- **WHEN** an ERT test saves a modified buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection with the current time fixed at 2026-07-15T10:00:00Z, and again at 2026-01-15T10:00:00Z
- **THEN** the saved `lastmod` lines are `lastmod = 2026-07-15T12:00:00+02:00` and `lastmod = 2026-01-15T11:00:00+01:00`

#### Scenario: The fall-back hour
- **WHEN** an ERT test saves a modified buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection with the current time fixed at 2026-10-25T00:30:00Z, and again at 2026-10-25T01:30:00Z
- **THEN** the saved `lastmod` lines are `lastmod = 2026-10-25T02:30:00+02:00` and `lastmod = 2026-10-25T02:30:00+01:00`

#### Scenario: The user's own time-stamp settings
- **WHEN** an ERT test sets the global `time-stamp-pattern` to `"10/Updated: <%Y>"`, puts `time-stamp` on the global `before-save-hook`, and saves a modified buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection with the current time fixed at 2026-07-15T10:00:00Z
- **THEN** the saved `lastmod` line is `lastmod = 2026-07-15T12:00:00+02:00`

#### Scenario: Global settings untouched
- **WHEN** an ERT test sets the global `time-stamp-format` to `%Y` and visits a procedure of a collection copy with `global-orgsyndb-mode` on
- **THEN** the default value of `time-stamp-format` is still `%Y`, and the buffer's local value differs from it

#### Scenario: Turned off
- **WHEN** an ERT test saves a modified Markdown procedure buffer with `orgsyndb-update-timestamps` nil, and saves another one, visited while the option was non-nil, after setting it to nil
- **THEN** neither `lastmod` line changed

#### Scenario: Only the front matter
- **WHEN** an ERT test removes the `lastmod` line from the front matter of `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, adds to its body a fenced code block holding the line `lastmod = 2020-01-01T00:00:00+01:00`, and saves it
- **THEN** that line of the body is unchanged

#### Scenario: The buffer's own settings come back
- **WHEN** an ERT test gives a buffer visiting a compound file, and one visiting a Markdown procedure with `orgsyndb-mode` off, a local `time-stamp-format` of `%Y` and `time-stamp` on the local `before-save-hook`, then turns `orgsyndb-mode` on and off in each
- **THEN** each buffer's local `time-stamp-format` is `%Y` and its local `before-save-hook` holds `time-stamp`

### Requirement: New procedure and new compound
`orgsyndb-new-procedure` SHALL read a title and, with a prefix argument, a format, `org` or `md`, and a language, `none`, `de` or `en`; without one it uses `org` and `none`. It runs `orgsyndb -C <collection> new`, adding `--md` for Markdown and `--lang <code>` for a language, then the title's words, and visits the file whose collection-relative path the program prints. When the run fails, it signals an error holding the program's error output.

`orgsyndb-new-compound` SHALL read a key, which must be a lowercase hyphenated slug that no compound file uses, and then, in the order of the application's compound template, `name`, the optional `name_de`, `formula`, `mw` as a number, `smiles`, and the optional `cas` and `structure_image`, empty input leaving an optional value out and the image being completed from `static/structures/`; then each declared compound field with `required = true`, in declared order: a choice with completion over its vocabulary's values, several for a `multiple` field; a boolean as yes or no; a number as a number; a text as text. It writes `compounds/<key>.toml` holding one `<key> = <value>` line per value read, in that order, with TOML strings, numbers, booleans and arrays of strings, and visits it.

#### Scenario: New Markdown procedure in German
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that records its arguments, creates `md/procedures/OSDB-0010-ethylacetat.de.md` and prints that path, and calls `orgsyndb-new-procedure` with a prefix argument and the answers `md`, `de` and `Ethylacetat herstellen`
- **THEN** the stub received `-C <collection> new --md --lang de Ethylacetat herstellen` as separate arguments, and the current buffer visits `md/procedures/OSDB-0010-ethylacetat.de.md`

#### Scenario: New compound with declared fields
- **WHEN** an ERT test calls `orgsyndb-new-compound` in a copy of the demo collection with the answers `ethanol`, `Ethanol`, `Ethanol`, `C2H6O`, `46.07`, `CCO`, `64-17-5`, an empty structure image, `CH-0099`, `alcohols` and `reagents`
- **THEN** `compounds/ethanol.toml` holds exactly the lines `name = "Ethanol"`, `name_de = "Ethanol"`, `formula = "C2H6O"`, `mw = 46.07`, `smiles = "CCO"`, `cas = "64-17-5"`, `item_number = "CH-0099"`, `chemical_class = ["alcohols"]` and `group = "reagents"`, in that order, and `orgsyndb index` of the copy lists `ethanol` without an `error`

### Requirement: Preview
`orgsyndb-page-url` SHALL return, for a file of a collection, `http://127.0.0.1:<port>/` followed by `procedures/<id>/` for a procedure, `sequences/<id>/` for a sequence and `compounds/<key>/` for a compound file, the ID in lower case, and by nothing for any other file; `<port>` is the user option `orgsyndb-preview-port`, 8000 by default.

`orgsyndb-serve` SHALL start `orgsyndb -C <collection> serve --port <port>` in the buffer `*orgsyndb serve <collection>*`, the collection's directory abbreviated as `abbreviate-file-name` does, unless a serve process of the package runs for the collection; `orgsyndb-stop-server` ends that process.

`orgsyndb-preview` SHALL show the page of the current file: with no serve process for the collection, it starts one as `orgsyndb-serve` does and calls `browse-url` on the page's URL once the process prints its `serving` line; with one running, it runs `orgsyndb -C <collection> build` in the background in the buffer `*orgsyndb build <collection>*` and calls `browse-url` when the build exits 0, or displays that buffer when it fails. When the current file is a procedure or sequence that the site does not publish, its message names the variant the page shows: the file tagged with the site's language from the index's `site_language`, else the file without a code, else the other.

`orgsyndb-preview-on-save-mode`, a buffer-local minor mode, SHALL start such a build after each save of its buffer once `orgsyndb-preview-delay` seconds pass without another save, when a serve process runs for the collection, without calling `browse-url`.

#### Scenario: Page URLs
- **WHEN** an ERT test calls `orgsyndb-page-url` on `org/procedures/OSDB-0007-ethyl-cinnamate.de.org`, `compounds/acetone.toml`, `md/sequences/SEQ-0001-aspirin-from-wintergreen.md` and `orgsyndb.toml` of a copy of the demo collection
- **THEN** the results are `http://127.0.0.1:8000/procedures/osdb-0007/`, `http://127.0.0.1:8000/compounds/acetone/`, `http://127.0.0.1:8000/sequences/seq-0001/` and `http://127.0.0.1:8000/`

#### Scenario: First preview starts the server
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that records its arguments, prints `serving http://127.0.0.1:8000/ (Ctrl-C to stop)` and then waits, replaces `browse-url` with a recorder, and calls `orgsyndb-preview` in a buffer visiting `compounds/acetone.toml` of a copy of the demo collection
- **THEN** the stub received `-C <collection> serve --port 8000`, and `browse-url` was called once with `http://127.0.0.1:8000/compounds/acetone/`

#### Scenario: Later preview builds
- **WHEN** the test calls `orgsyndb-preview` again while the stub server runs, the stub answering `build` with exit 0
- **THEN** the stub received `-C <collection> build`, and `browse-url` was called a second time with the same URL after the build exited

#### Scenario: Unpublished variant
- **WHEN** an ERT test calls `orgsyndb-preview` with the stub in a buffer visiting `org/procedures/OSDB-0007-ethyl-cinnamate.org` of a copy of the demo collection, whose site language is `de`
- **THEN** the message names `OSDB-0007-ethyl-cinnamate.de.org`

### Requirement: PDF
`orgsyndb-pdf` SHALL run `orgsyndb -C <collection> pdf` in the background in a buffer and, when it exits 0 and the current file is a procedure, visit in another window the file of the collection's `pdf/` whose name begins with the procedure's ID followed by `-`; when the run fails it displays the buffer.

#### Scenario: The procedure's PDF
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that, for `pdf`, creates `pdf/OSDB-0007-ethyl-cinnamate.de.pdf` and exits 0, and calls `orgsyndb-pdf` in a buffer visiting `org/procedures/OSDB-0007-ethyl-cinnamate.org` of a copy of the demo collection
- **THEN** after the run a buffer visits `pdf/OSDB-0007-ethyl-cinnamate.de.pdf`

### Requirement: Structure window
`orgsyndb-structure-mode`, a buffer-local minor mode, SHALL show the buffer `*orgsyndb structure*` in a side window and, whenever Emacs has been idle for `orgsyndb-structure-delay` seconds after a command, fill it for the compound at point: the identifier of "Definitions and references" when it is a compound key, or in a compound file the file's own compound. The buffer shows the compound's structure image, the file `static/<structure_image>` of the collection, when the compound sets one and Emacs can display its type, and below it the compound's name and formula. When point is on no compound the buffer keeps its content. Turning the mode off deletes the side window.

#### Scenario: Image and text
- **WHEN** an ERT test turns on `orgsyndb-structure-mode` in a buffer of a copy of the demo collection holding `isopentyl-acetate` and `acetone`, and runs the update with point on each in turn
- **THEN** after the first the structure buffer holds an image whose file is the collection's `static/structures/isopentyl-acetate.svg`, where Emacs can display SVG, and the text `Isopentyl acetate`; after the second it holds no image and the text `Acetone`

### Requirement: Command menu
`orgsyndb-mode-map` SHALL bind `C-c C-;` to `orgsyndb-dispatch` and bind no other key. `orgsyndb-dispatch` is a transient prefix whose suffixes are `orgsyndb-new-procedure`, `orgsyndb-new-compound`, `orgsyndb-insert-compound`, `orgsyndb-visit-variant`, `orgsyndb-create-translation`, `orgsyndb-validate`, `orgsyndb-preview`, `orgsyndb-serve`, `orgsyndb-stop-server`, `orgsyndb-pdf`, `orgsyndb-structure-mode`, `orgsyndb-preview-on-save-mode` and `orgsyndb-refresh-index`.

#### Scenario: One binding
- **WHEN** an ERT test maps over the bindings of `orgsyndb-mode-map`
- **THEN** the only command bound is `orgsyndb-dispatch`, on `C-c C-;`, and the suffixes of `orgsyndb-dispatch` are the thirteen commands named above

### Requirement: Package ERT suite
The repository SHALL ship `tests/el/orgsyndb-tests.el`, an ERT suite that proves each scenario of this capability stated as an ERT test, each test naming its scenario in its docstring. It runs with `emacs -Q --batch -l <repo>/tests/el/orgsyndb-tests.el -f ert-run-tests-batch-and-exit` from any working directory, loads the package from `emacs/` relative to its own location, and works on temporary copies of `tests/fixtures/collection/` and `examples/demo/`. It runs the repository's `tools/orgsyndb` for `index` and `validate`, a stub program for the other subcommands, and no browser. A test that needs the Org export skips itself, naming `ox-hugo`, when the application's `.emacs-batch/elpa/ox-hugo/` does not exist. `tests/test_elisp.py` runs the suite under pytest, as it runs the front end's, passing when the command exits 0 with no unexpected result, and skipping with a reason that names `emacs` when `emacs` is absent; the same file runs the byte compilation of "Package files".

#### Scenario: Package suite under pytest
- **WHEN** `python3 -m pytest tests/test_elisp.py` runs with `emacs` on `PATH` and ox-hugo cached
- **THEN** it passes, having run the package's ERT suite with no failed or skipped test
