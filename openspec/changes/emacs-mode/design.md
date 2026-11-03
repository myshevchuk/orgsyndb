## Context

The application is a Python program in a Git checkout that users run by
path or through a symlink. Collections are separate directories marked
by `orgsyndb.toml`. The Org front end of the export, `tools/osdb-org.el`,
already reads Org keywords, timestamps and the scope table without
loading Org. `orgsyndb validate` takes about two seconds on the demo,
most of it the Emacs batch export, and reports `path:field: severity:
message` lines without line numbers; the problems of an Org source's
export name `build/export/<stem>.md`. `collection-index` adds
`orgsyndb index`, a JSON description of a collection, Org sources by
name only.

## Goals / Non-Goals

**Goals:** completion, navigation, diagnostics, timestamps and preview
for the files of a collection, with no package outside Emacs 29.1 and
no second copy of the schema. The one exception is the new-compound
command, which holds the order of the built-in compound keys, as the
application's compound template writes them, and the fact that `mw`
is a number; the index gives the keys themselves.

**Non-Goals:** links in procedure bodies (deferred until the build
supports them), the reagents-table helper, a preview in the other
language, live reload of the browser, a language server, publication
on MELPA.

## Decisions

### Shipped in the application, loaded from its checkout

The package lives in `emacs/` and calls the program of the same
checkout, `<app>/tools/orgsyndb`, found from the package file's true
name. Index, problem lines and package change together, so no version
is negotiated. A user who has the checkout loads it with
`load-path`, a package manager's local recipe, or `package-vc-install`
with `:lisp-dir "emacs"`. `orgsyndb-program` overrides the path.

Rejected: a separate repository. Every schema change would need a
release of both, and the package would have to detect which program it
talks to.

### The Org front end moves into `emacs/`

The package needs `osdb-org.el` at load time for its Org checks and its
Org front-matter reader. With the file in `emacs/`, a package manager
that installs only that directory, and the byte compiler, find
everything; the export loads it from `<app>/emacs/`. The file keeps its
name and its `osdb-org-` prefix, which the export, its ERT suite and the
specs use throughout.

Rejected: adding `<app>/tools/` to `load-path` at run time. It breaks
byte compilation and any install that copies only the package
directory.

### Two sources of collection data

TOML files reach Emacs through `orgsyndb index`; Org sources are read
in Emacs with `osdb-org-front-matter`, keywords and scope table,
cached by modification time. Python keeps reading no Org source, and
Emacs needs no TOML parser.

The index is fetched synchronously the first time a feature of a
collection needs it, then refreshed in the background after every save
of a collection file, so that a new Org source joins the list of
procedures; the run costs a fraction of the validation that follows
the same save. A failed refresh keeps the previous index and reports
the program's error once. Changes made outside Emacs show after the
next save or `orgsyndb-refresh-index`.

### Activation by location

`global-orgsyndb-mode` is a globalized minor mode. Its turn-on function
looks for `orgsyndb.toml` above the visited file, caching the answer per
directory, and classifies the file by its path in the collection. The
major mode does not matter, so Markdown files work without
markdown-mode.

### One completion function, contexts from the text

`orgsyndb-completion-at-point` recognizes a fixed set of contexts by
looking at the text around point: the key being written at the start of
a front-matter line; the string or bare value after a key, including
inside arrays and inline tables, where the innermost enclosing key
decides (`compound = "` inside `products`, `substrates = ["` inside a
scope entry); the `:key value` pairs of `#+HUGO_CUSTOM_FRONT_MATTER`;
`#+HUGO_TAGS`; the cells of the `substrates` and `products` columns of
an Org scope table. Outside these it returns nil, so other completion
functions run. Candidates are keys or values, never prose; their
annotations carry names and labels. Matching a compound by its name is
the job of `orgsyndb-insert-compound`, whose candidates are names.

Rejected: a TOML or Lisp parser over the buffer. The text being
completed is incomplete by definition and would not parse.

### Diagnostics in two layers

The Flymake backend reports two lists for the buffer: the Org front
end's problems, computed from the buffer text on every Flymake run, and
the problems the last `orgsyndb validate` reported for the file. The
validation runs once per save of a collection file, in the background,
for the whole collection, since variants, unique values and sequences
cross files; when it finishes, every open buffer of the collection
gets its share.

The run's problem lines come from two programs: the export's, on paths
in `org/procedures/`, and the validator's. A run that stops at the
export replaces only the export's problems and keeps the validator's
earlier ones, which are still the best information; it also says in
the echo area why the validation did not run, since a subdirectory or
an unreadable file stops it without touching any open buffer. An
export problem that the first layer reports with the same field,
severity and message is left out; the export checks problems the
first layer cannot, such as invalid UTF-8, and those stay.

A problem's field is placed on a line: the line a TOML parse error
names; the key's line in Markdown front matter or a TOML file, a table
header such as `[[products]]` included; in Org, the keyword that writes the field
(`title` on `#+TITLE`, `tags` on `#+HUGO_TAGS`, `slug` on
`#+HUGO_SLUG`, `date` on `#+CREATED`, `lastmod` on
`#+LAST_MODIFIED`, `ai_model` on `#+AI_MODEL`), the `#+NAME: scope`
line for `scope`, or the custom-front-matter line holding `:<key>`.
An indexed field such as `scope[2].time` goes to its top-level key; a
field with no line goes to line 1.

The Flycheck adapter calls the same collection of diagnostics and
converts them. It defines its checker only once Flycheck is loaded, so
the package never requires Flycheck.

### Timestamps through `time-stamp`

The mode sets `time-stamp-active`, `time-stamp-pattern` (to nil, since
a pattern overrides the other variables), `time-stamp-start`,
`time-stamp-end`, `time-stamp-format`, `time-stamp-time-zone`,
`time-stamp-line-limit` and `system-time-locale` buffer-locally and puts
`time-stamp` on the buffer's `before-save-hook`. The user's global
values, and a global `time-stamp` hook, stay in force everywhere else;
in a collection buffer such a hook runs `time-stamp` a second time with
the buffer's settings, which rewrites the same stamp.

Org uses `%Y-%02m-%02d %3a %02H:%02M:%02S` in Europe/Berlin with
`system-time-locale` `C` for the English weekday. `time-stamp` has no
documented conversion for a `+HH:MM` offset (`%5z` writes `+0200`,
which TOML rejects), so for Markdown a function earlier on the same hook
takes the current Europe/Berlin offset, writes it into the buffer-local
format as literal text, and sets the buffer-local
`time-stamp-time-zone` to that fixed offset. The time and the offset
then come from one offset, and the text names the instant of the save
even when the clock changes between the two functions.

### Preview through `serve` and `build`

`orgsyndb serve` builds once and then serves `public/` from disk, so a
later `orgsyndb build` changes what it serves. The mode keeps one serve
process per collection, runs `build` for each later preview, and opens
the page of the file being edited: `/procedures/<id>/`,
`/sequences/<id>/` or `/compounds/<key>/`, in lower case. The browser
is not reloaded; there is no live reload. When the file is not the
variant the site publishes, the message says which variant the page
shows.

### One command at a time

`validate`, `build`, `pdf` and the first build of `serve` all run the
export, which clears and rebuilds the collection's `build/` staging
directories. The package queues them per collection, so that a
validation on save and a preview build never overlap; a queued
validation or build is not queued twice, since one run covers every
save before it. `serve` leaves the queue once it prints its `serving`
line, when it only reads `public/`. Runs started outside Emacs are not
coordinated.

### One key binding

The mode binds only `C-c C-;`, which neither Org nor markdown-mode
binds, to a transient menu. Everything else uses the standard commands:
`completion-at-point`, `xref-find-definitions`, `xref-find-references`
and `eldoc`.

### Tests

Pure functions carry the logic the scenarios test: file kinds, page
URLs, problem locations, the completion candidates at a given point,
the Org front-matter reader. ERT tests run the real `orgsyndb index`
on copies of the test collection and the demo, and a stub program for
the commands that start processes. The suite runs in the Emacs 29
workflow through `tests/test_elisp.py`; that run is the check against
Emacs 29.1, since the owner's Emacs is newer.
