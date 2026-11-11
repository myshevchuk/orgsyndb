## MODIFIED Requirements

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
- **WHEN** an ERT test gives a buffer visiting the collection's `orgsyndb.toml`, and one visiting a Markdown procedure with `orgsyndb-mode` off, a local `time-stamp-format` of `%Y` and `time-stamp` on the local `before-save-hook`, then turns `orgsyndb-mode` on and off in each
- **THEN** each buffer's local `time-stamp-format` is `%Y` and its local `before-save-hook` holds `time-stamp`

### Requirement: Command menu
`orgsyndb-mode-map` SHALL bind `C-c C-;` to `orgsyndb-dispatch` and bind no other key. `orgsyndb-dispatch` is a transient prefix whose suffixes are `orgsyndb-new-procedure`, `orgsyndb-insert-compound`, `orgsyndb-visit-variant`, `orgsyndb-create-translation`, `orgsyndb-validate`, `orgsyndb-preview`, `orgsyndb-serve`, `orgsyndb-stop-server`, `orgsyndb-pdf`, `orgsyndb-structure-mode`, `orgsyndb-preview-on-save-mode` and `orgsyndb-refresh-index`.

#### Scenario: One binding
- **WHEN** an ERT test maps over the bindings of `orgsyndb-mode-map`
- **THEN** the only command bound is `orgsyndb-dispatch`, on `C-c C-;`, and the suffixes of `orgsyndb-dispatch` are the twelve commands named above

### Requirement: Structure window
`orgsyndb-structure-mode`, a buffer-local minor mode, SHALL show the buffer `*orgsyndb structure*` in a side window and, whenever Emacs has been idle for `orgsyndb-structure-delay` seconds after a command, fill it for the compound at point: the identifier of "Definitions and references" when it is a compound key. The buffer shows the compound's structure image, the file `static/structures/<key>.svg` of the collection, or `.png` when there is no SVG (compound-registry "Structure images by key"), when there is one and Emacs can display its type, and below it the compound's name and formula from the index, those it has. When point is on no compound the buffer keeps its content. Turning the mode off deletes the side window.

#### Scenario: Image and text
- **WHEN** an ERT test turns on `orgsyndb-structure-mode` in a buffer of a copy of the demo collection holding `isopentyl-acetate` and `acetone`, and runs the update with point on each in turn
- **THEN** after the first the structure buffer holds an image whose file is the collection's `static/structures/isopentyl-acetate.svg`, where Emacs can display SVG, and the text `Isopentyl acetate`; after the second it holds no image and the text `Acetone`

### Requirement: Collection data
The package SHALL keep, per collection, the index that `orgsyndb index` prints (collection-index "Index data"), parsed with JSON objects as alists keyed by symbols, arrays as lists, `null` as nil and `false` as `:false`. `orgsyndb-index` returns the index of the current buffer's collection, running the program synchronously when the package holds none for it yet. After a buffer in `orgsyndb-mode` is saved, the package runs the program in the background and replaces the collection's index when the run succeeds. A run that exits non-zero leaves the index unchanged and shows the program's error output in a message. `orgsyndb-refresh-index` runs it again for the current collection.

`orgsyndb-procedures` returns one record per entry of the index's `procedures`: the entry, with the `front_matter` of an Org source taken from `osdb-org-front-matter` (org-export "Front matter of an Org source") of the visiting buffer's text when a buffer visits the file, and of the file otherwise, read again when the file's modification time changes.

#### Scenario: First use
- **WHEN** an ERT test calls `orgsyndb-index` in a buffer visiting a file of a copy of the test collection
- **THEN** it returns the parsed index, whose `compounds` holds 21 entries

#### Scenario: Refresh after a save
- **WHEN** an ERT test fetches the index of a copy of the test collection, then creates `md/procedures/OSDB-0010-test.md` through a buffer in `orgsyndb-mode`, saves it and waits for the background run to finish
- **THEN** the index lists the procedure `OSDB-0010`

#### Scenario: A new Org source after a save
- **WHEN** an ERT test fetches the index of a copy of the demo collection, then creates `org/procedures/OSDB-0010-test.org` through a buffer in `orgsyndb-mode`, saves it and waits for the background run to finish
- **THEN** `orgsyndb-procedures` holds a record whose `path` is `org/procedures/OSDB-0010-test.org`

#### Scenario: A failed run keeps the index
- **WHEN** an ERT test fetches the index of a copy of the test collection, then sets `orgsyndb-program` to a script that writes `boom` to stderr and exits 1, and calls `orgsyndb-refresh-index`
- **THEN** `orgsyndb-index` returns the earlier index, and the last message contains `boom`

#### Scenario: Org records
- **WHEN** an ERT test calls `orgsyndb-procedures` for a copy of the demo collection
- **THEN** the record of `org/procedures/OSDB-0007-ethyl-cinnamate.org` has the front-matter `title` `Ethyl cinnamate` and `status` `draft`

### Requirement: Definitions and references
The mode SHALL put an `xref` backend on the buffer's `xref-backend-functions`. Its identifier at point is, anywhere in the buffer, including Org and Markdown body text: a maximal run of lowercase letters, digits and hyphens that is a registry compound key; a procedure ID `OSDB-NNNN`; or a sequence ID `SEQ-NNNN`.
- A compound key's definition is line 1 of the buffer `*orgsyndb <key>*`, which the backend fills from the key's entry in the index's `compounds`: the substance's name and, those it has, its German name, formula, molar mass, CAS number, article number and short name, one per line, and, when the entry has a `url`, that address as a button that calls `browse-url` on it.
- An ID's definition is one file of that ID among the procedures or sequences: the file whose language code is the current file's code, else the file without a code, else the first file in name order.
- A compound key's references are the lines of the collection's procedure and sequence files that contain the key with no lowercase letter, digit or hyphen directly before or after it. An ID's references are the lines of those files that contain the ID.
- The identifiers offered for completion are the compound keys and the IDs.

#### Scenario: Compound definition
- **WHEN** an ERT test, in a buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, asks the backend for the definitions of the identifier at point with point on `acetic-anhydride` in `substrates`
- **THEN** there is one definition, at line 1 of the buffer `*orgsyndb acetic-anhydride*`, which holds `Acetic anhydride` and no button, the test collection's registry being a file

#### Scenario: Procedure definition in the reader's language
- **WHEN** an ERT test asks for the definitions of `OSDB-0001` at point in `md/sequences/SEQ-0001-aspirin-from-wintergreen.md`, and in `md/sequences/SEQ-0001-aspirin-from-wintergreen.de.md`, of a copy of the demo collection
- **THEN** the definitions are `org/procedures/OSDB-0001-salicylic-acid.org` and `org/procedures/OSDB-0001-salicylic-acid.de.org`, one each

#### Scenario: Compound references
- **WHEN** an ERT test asks for the references of `acetic-anhydride` in a copy of the test collection
- **THEN** they include a line of `md/procedures/OSDB-0002-aspirin.md` and one of `md/procedures/OSDB-0002-aspirin.de.md`

#### Scenario: A substance with a page
- **WHEN** an ERT test asks for the definition of a compound key whose index entry has the `url` `http://lab.example.org/lab/registry/substances/acetone/`, with `browse-url` replaced by a recorder, and presses the buffer's button
- **THEN** `browse-url` was called once with that address

### Requirement: Preview
`orgsyndb-page-url` SHALL return, for a file of a collection, `http://127.0.0.1:<port>/` followed by `procedures/<id>/` for a procedure and `sequences/<id>/` for a sequence, the ID in lower case, and by nothing for any other file; `<port>` is the user option `orgsyndb-preview-port`, 8000 by default.

`orgsyndb-serve` SHALL start `orgsyndb -C <collection> serve --port <port>` in the buffer `*orgsyndb serve <collection>*`, the collection's directory abbreviated as `abbreviate-file-name` does, unless a serve process of the package runs for the collection; `orgsyndb-stop-server` ends that process.

`orgsyndb-preview` SHALL show the page of the current file: with no serve process for the collection, it starts one as `orgsyndb-serve` does and calls `browse-url` on the page's URL once the process prints its `serving` line; with one running, it runs `orgsyndb -C <collection> build` in the background in the buffer `*orgsyndb build <collection>*` and calls `browse-url` when the build exits 0, or displays that buffer when it fails. When the current file is a procedure or sequence that the site does not publish, its message names the variant the page shows: the file tagged with the site's language from the index's `site_language`, else the file without a code, else the other.

`orgsyndb-preview-on-save-mode`, a buffer-local minor mode, SHALL start such a build after each save of its buffer once `orgsyndb-preview-delay` seconds pass without another save, when a serve process runs for the collection, without calling `browse-url`.

#### Scenario: Page URLs
- **WHEN** an ERT test calls `orgsyndb-page-url` on `org/procedures/OSDB-0007-ethyl-cinnamate.de.org`, `md/sequences/SEQ-0001-aspirin-from-wintergreen.md` and `orgsyndb.toml` of a copy of the demo collection
- **THEN** the results are `http://127.0.0.1:8000/procedures/osdb-0007/`, `http://127.0.0.1:8000/sequences/seq-0001/` and `http://127.0.0.1:8000/`

#### Scenario: First preview starts the server
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that records its arguments, prints `serving http://127.0.0.1:8000/ (Ctrl-C to stop)` and then waits, replaces `browse-url` with a recorder, and calls `orgsyndb-preview` in a buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the demo collection
- **THEN** the stub received `-C <collection> serve --port 8000`, and `browse-url` was called once with `http://127.0.0.1:8000/procedures/osdb-0002/`

#### Scenario: Later preview builds
- **WHEN** the test calls `orgsyndb-preview` again while the stub server runs, the stub answering `build` with exit 0
- **THEN** the stub received `-C <collection> build`, and `browse-url` was called a second time with the same URL after the build exited

#### Scenario: Unpublished variant
- **WHEN** an ERT test calls `orgsyndb-preview` with the stub in a buffer visiting `org/procedures/OSDB-0007-ethyl-cinnamate.org` of a copy of the demo collection, whose site language is `de`
- **THEN** the message names `OSDB-0007-ethyl-cinnamate.de.org`

### Requirement: Problem locations
`orgsyndb-problem-location` SHALL take a collection directory, a problem's path relative to it, the problem's field and its message, and return the file and the line, counting from 1, where the problem belongs:
- The file is the path, except that `build/export/<stem>.md` maps to `org/procedures/<stem>.org`.
- The key is the field up to its first `[` or `.`.
- A `front_matter` or `toml` problem whose message holds `at line <n>` belongs on line `<n>` of the file, the line that `tomllib` names.
- In a Markdown file, the line is the first line of the front matter that begins, after optional blanks, with the key, bare or in double quotes, followed by optional blanks and `=`, or that is a table header whose first dotted part is the key, such as `[[products]]`.
- In an Org file, the line is the first line of the keyword that writes the key: `#+TITLE` for `title`, `#+HUGO_SLUG` for `slug`, `#+HUGO_TAGS` for `tags`, `#+CREATED` for `date`, `#+LAST_MODIFIED` for `lastmod`, `#+AI_MODEL` for `ai_model`, the keyword itself for a field that begins with `#+`; the `#+NAME: scope` line for `scope`; otherwise the first `#+HUGO_CUSTOM_FRONT_MATTER` line holding `:<key>` followed by a blank or the line's end. Keyword names match in any case.
- In the registry file, `build/registry.json`, the line is 1.
- The line is 1 when nothing matches.

#### Scenario: Export problem on the Org source
- **WHEN** an ERT test calls `orgsyndb-problem-location` for a copy of the demo collection with the path `build/export/OSDB-0007-ethyl-cinnamate.md`, the message `must be a number`, and the fields `products[1].yield_percent`, `working_time`, `title` and `file_name`
- **THEN** each result names `org/procedures/OSDB-0007-ethyl-cinnamate.org`, with the lines 18, 13, 1 and 1

#### Scenario: Markdown fields and the registry
- **WHEN** an ERT test calls it for a copy of the test collection with `md/procedures/OSDB-0002-aspirin.md` and `status`, and with `build/registry.json` and `substances`, each with the message `unknown`
- **THEN** the lines are 8 and 1

#### Scenario: Line of a front-matter error
- **WHEN** an ERT test calls it for a copy of the test collection with `md/procedures/OSDB-0002-aspirin.md`, the field `front_matter` and the message `invalid TOML: Invalid value (at line 3, column 8)`
- **THEN** the line is 3

### Requirement: Turning the mode on
`global-orgsyndb-mode` SHALL turn on `orgsyndb-mode`, whatever the major mode, in each buffer visiting a file whose kind is not nil. `orgsyndb-collection-root` returns the collection of a file, the nearest directory at or above the file's directory that holds `orgsyndb.toml`, or nil. `orgsyndb-file-kind` returns the kind of a file from its path relative to its collection:
- `org-procedure` for a `.org` file directly in `org/procedures/`;
- `md-procedure` for a `.md` file directly in `md/procedures/`;
- `sequence` for a `.md` file directly in `md/sequences/`;
- `settings` for `orgsyndb.toml`;
- nil for every other file, and for a file outside any collection.

The mode's lighter is ` OSDB`. The features of the following requirements act only in buffers whose kind they name.

#### Scenario: Kinds
- **WHEN** an ERT test calls `orgsyndb-file-kind` on these files of a copy of the demo collection: `org/procedures/OSDB-0007-ethyl-cinnamate.de.org`, `md/procedures/OSDB-0002-aspirin.md`, `md/sequences/SEQ-0001-aspirin-from-wintergreen.md`, `orgsyndb.toml`, `build/export/OSDB-0007-ethyl-cinnamate.md` and `static/structures/isopentyl-acetate.svg`
- **THEN** it returns `org-procedure`, `md-procedure`, `sequence`, `settings`, nil and nil

#### Scenario: Turned on by visiting
- **WHEN** an ERT test turns on `global-orgsyndb-mode` and visits `md/procedures/OSDB-0002-aspirin.md` of a copy of the demo collection and a `.md` file in a temporary directory outside any collection
- **THEN** `orgsyndb-mode` is on in the first buffer and off in the second

## ADDED Requirements

### Requirement: Completion in sequences
`orgsyndb-completion-at-point` SHALL offer, in a buffer of kind `sequence`, inside the front matter: at the start of a line, the sequence keys that the front matter does not set yet; inside the string of `target`, the compound keys; inside the string of `procedure` in a step, the procedure IDs, each annotated with its title; after `entry = ` in a step, the entry numbers `1` to `n` of the general procedure that the step's `procedure` names, each annotated with the compound keys of that entry's products, and nothing when the step names a specific procedure.

#### Scenario: Step procedure
- **WHEN** an ERT test, in a buffer visiting `md/sequences/SEQ-0001-aspirin-from-wintergreen.md` of a copy of the demo collection, calls `orgsyndb-completion-at-point` with point after `OSDB-000` inside `steps = [{ procedure = "OSDB-000" }]`
- **THEN** the completions are the nine IDs `OSDB-0001` to `OSDB-0009`, and `OSDB-0007` is annotated with text containing `Ethyl cinnamate`

#### Scenario: Step entry
- **WHEN** the test does the same with point after `entry = ` in `{ procedure = "OSDB-0009", entry = }`
- **THEN** the completions are `("1" "2" "3")`, and `1` is annotated with text containing `1-biphenyl-4-yl-ethanol`

#### Scenario: Step entry of an Org general procedure
- **WHEN** an ERT test copies `tests/fixtures/export/OSDB-0909-scope-table.org` into `org/procedures/` of a copy of the demo collection and does the same in `{ procedure = "OSDB-0909", entry = }`
- **THEN** the completions are `("1" "2" "3")`, and `1` is annotated with text containing `ethyl-acetate` and `propyl-acetate`

### Requirement: New procedure
`orgsyndb-new-procedure` SHALL read a title and, with a prefix argument, a format, `org` or `md`, and a language, `none`, `de` or `en`; without one it uses `org` and `none`. It runs `orgsyndb -C <collection> new`, adding `--md` for Markdown and `--lang <code>` for a language, then the title's words, and visits the file whose collection-relative path the program prints. When the run fails, it signals an error holding the program's error output.

#### Scenario: New Markdown procedure in German
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that records its arguments, creates `md/procedures/OSDB-0010-ethylacetat.de.md` and prints that path, and calls `orgsyndb-new-procedure` with a prefix argument and the answers `md`, `de` and `Ethylacetat herstellen`
- **THEN** the stub received `-C <collection> new --md --lang de Ethylacetat herstellen` as separate arguments, and the current buffer visits `md/procedures/OSDB-0010-ethylacetat.de.md`

## REMOVED Requirements

### Requirement: Completion in sequences and compound files
**Reason**: Collections hold no compound files; completion in sequences is kept as Completion in sequences.
**Migration**: None.

### Requirement: New procedure and new compound
**Reason**: Substances are created in the lab application's registry; creating a procedure is kept as New procedure.
**Migration**: Create a substance on the lab application's page `/lab/registry/substances/new/`.
