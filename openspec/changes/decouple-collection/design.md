## Context

This is change 4. Changes 1–3 are archived, and their specs in
`openspec/specs/` govern everything this change does not modify.

State on `main` at the start:

- `tools/build.fish` (fish, 332 lines) orchestrates the build. It locates
  the repository from its own path and reads `org/procedures/`,
  `md/procedures/` and `site/static/` there. Every generated file goes into
  the same checkout: `build/`, `public/`, `pdf/`, `site/resources/`,
  `site/.hugo_build.lock`, `.emacs-batch/` and `.tools/`.
- All of its logic other than argument parsing and step order already
  lives in `tools/pipeline.py` and `tools/validate.py`, which it runs as
  subprocesses.
- `site/hugo.toml` mounts `../build/export` and `../md/procedures`
  relative to `site/`.
- The repository holds only sample data (tag `sample-data`).

The goal is a public application repository and one or more private data
repositories that the application builds.

## Goals / Non-Goals

**Goals:**

- A collection is self-contained: a git repository holding only a
  collection has everything needed to rebuild its site with any checkout of
  the application.
- The application checkout holds no procedure and receives no build output.
- Python 3.14 and the existing external tools are the only requirements;
  fish is gone.
- Every behaviour the specs fix for `build.fish` keeps its meaning under
  `tools/orgsyndb`, unless this change says otherwise.

**Non-Goals:**

- Deployment, server-side builds, web editing, authentication. These are
  later changes; this one must only not preclude them.
- Per-collection site settings (title, vocabulary, theme overrides).
  `format = 1` reserves room for them.
- Moving the fetched-tool caches out of the application (for example to
  `$XDG_CACHE_HOME`).
- Installing the application as a package; it runs from its checkout.

## Decisions

### D1 A collection is a directory with an `orgsyndb.toml` marker

Layout:

```text
<collection>/
  orgsyndb.toml        format = 1
  org/procedures/      Org sources (optional)
  md/procedures/       Markdown sources (optional)
  static/              copied into the site; structure images in structures/
  build/ public/ pdf/  generated, ignored by the collection's .gitignore
```

`orgsyndb.toml` must be a TOML table whose only key is `format`, with the
integer value `1`. It is the version of the contract between a collection
and the application; a future layout change raises it, and an application
that does not know a format refuses the collection instead of misreading
it. Unknown keys are errors so that a mistyped future setting is not
silently ignored.

Rejected: no marker, with `-C` pointing at any directory. Then a typo in a
path builds an empty site with exit 0, and nothing records which layout a
data repository follows.

### D2 The collection is chosen by `-C DIR`, else found from the working directory

`-C DIR` (or `--collection DIR`) comes before the subcommand, as in `git -C`
and `make -C`. Without it, the program walks from the working directory up
to the file-system root and takes the first directory holding
`orgsyndb.toml`. A `-C` directory without the marker is an error; there is
no fallback search from it.

The commands that need no collection never look for one: `help`,
`check-deps`, `init`, and `validate` with arguments.

Rejected: an `ORGSYNDB_COLLECTION` environment variable (a third way to say
the same thing, and invisible in shell history); defaulting to the demo
collection (a mistyped directory would quietly build sample data).

### D3 Everything generated goes into the collection

`build/`, `public/` and `pdf/` keep their names, now relative to the
collection. Hugo's `resourceDir` moves to `<collection>/build/hugo-resources`
and Hugo runs with `--noBuildLock`, so a build writes nothing under the
application's `site/`. The application keeps only `.emacs-batch/` and
`.tools/`, because their contents are pinned by the application's version,
not by any collection.

This keeps the integration tests' paths: they read `<root>/public`,
`<root>/build/export` and `<root>/pdf` with `root` now the collection.

`--noBuildLock` is safe because a single collection's build was never safe
to run twice concurrently anyway (the export directory swap), and two
collections no longer share any output.

### D4 Hugo configuration: a static file plus a generated overlay

`site/hugo.toml` keeps every site-wide key but drops `publishDir` and
`module.mounts`. Before Hugo runs, the build writes
`<collection>/build/hugo.toml`:

```toml
publishDir = "<collection>/public"
resourceDir = "<collection>/build/hugo-resources"

[[module.mounts]]   # <app>/site/content     -> content
[[module.mounts]]   # <collection>/build/export -> content/procedures, /OSDB-*.md
[[module.mounts]]   # <collection>/md/procedures -> content/procedures, /OSDB-*.md
[[module.mounts]]   # <collection>/static     -> static
```

and runs `hugo --source <app>/site --config <app>/site/hugo.toml,<overlay>
--minify --quiet --noBuildLock`. Paths are absolute and written as TOML
basic strings by `pipeline.toml_string`, so spaces and quotes are safe.
`pipeline.hugo_overlay(site, collection)` is a pure function and is tested
without Hugo.

Only the overlay defines `module.mounts`, so no array-merge rule of Hugo's
is relied on. Hugo still adds its default mounts for the components the
overlay does not mention (layouts, assets, data, i18n, archetypes), all
from `<app>/site/`.

Verified with Hugo 0.162.1: the built `public/` is byte-identical to the
one the old configuration produced from the same sources, and with
`--noBuildLock` nothing is written under `site/`.

Rejected: absolute paths in `site/hugo.toml` (not portable); symlinking the
collection into `site/` (writes into the application, breaks with two
collections); `HUGO_*` environment variables (they cannot express arrays of
tables).

### D5 The entry point is a Python program, not a shell script

`tools/orgsyndb` is a stdlib-only Python 3.14 program with a
`#!/usr/bin/env python3` shebang. It imports `pipeline` and `validate`
from its own directory and calls them in-process; `pipeline.py`'s CLI stays
as low-level plumbing that the tests drive.

A POSIX `sh` script would suffice for the step order, but not for the parts
around it without either duplicating Python or calling it for every
decision: the collection walk, TOML marker validation, option parsing for
three subcommands, the port check, version probing, the serve-line
handshake, and quoting of paths with spaces. Python is already required,
the rest of the tooling and every test is Python, and the program becomes
importable and testable in-process. Startup cost is negligible next to
Emacs and Hugo.

Conventions carried over from `build.fish`: `==> ` step lines, errors as
`orgsyndb: error: <message>`, exit 0/1/2, `TZ=Europe/Berlin` and
`LC_TIME=C` for every child process, the same required-tool checks and
`sudo dnf install` hints, and no `sudo` ever. `pipeline.PROG` names the
program in messages the module prints, so helper warnings say `orgsyndb:`
when called from it.

Rejected: bash (one more language with no gain over Python); a Makefile
(the steps are not file-dependency driven, and recovery logic does not fit
make); keeping fish (unusual and absent on servers).

### D6 The pre-commit hook is POSIX `sh` and belongs to the collection's repository

The hook resolves its own path with `readlink -f`, so it works both through
`core.hooksPath=<app>/tools/hooks` and as a symlink in `.git/hooks/`, and
runs `<app>/tools/orgsyndb -C <top of work tree> validate`. It therefore
validates a collection that is the root of its repository, which is the
intended layout of a private data repository. Nothing enables it.

### D7 The samples become the demo collection `examples/demo/`

`org/`, `md/` and `site/static/structures/` move there with `git mv`, with
an `orgsyndb.toml` and the same `.gitignore` that `init` writes. The demo
is both documentation ("this is what a collection looks like") and the
tests' default input.

Next-ID history: `candidate_names` runs `git -C <collection> log -- org/procedures
md/procedures`, whose paths are relative to the collection, and accepts a
collection anywhere inside a work tree instead of only at its top. Inside
the application repository this sees the demo's history from this change
on; IDs deleted before the move are not seen. That is acceptable for sample
data.

### D8 `init DIR` creates an empty collection

It creates `DIR` when missing, refuses when `DIR/orgsyndb.toml` exists,
and writes `orgsyndb.toml`, `.gitignore` (`/build/`, `/public/`, `/pdf/`),
and the empty directories `org/procedures/`, `md/procedures/` and
`static/structures/`. It does not run `git init` and writes no hook
configuration. Empty directories are lost on clone; every subcommand treats
a missing source tree as empty, so that is harmless.

### D9 Validator default static directory

`--static-dir` defaults to `static` in the working directory. The program
always passes it explicitly; the default serves a person running
`tools/validate.py` from a collection root. The vocabulary default is
unchanged (`<app>/site/data/reaction_types.toml`): the vocabulary is part of
the schema, not of the data.

### D10 `export.el` keeps temporary files beside the staging directory

The temporary directory is `<parent of STAGING_DIR>/tmp/`, that is
`<collection>/build/tmp/`, computed from the command line before package.el
or Org load. Recovery already empties `build/tmp/`. The Emacs directories
stay in `<app>/.emacs-batch/`.

### D11 Reading the inherited specs

Scenarios in specs this change does not modify still say `tools/build.fish
<subcommand>` and name paths such as `org/procedures/`, `build/` or
`public/` relative to "the repository". Until archive rewrites them, read
`tools/build.fish X` as `tools/orgsyndb -C <collection> X`, "temporary
repository copy" as "temporary application copy and collection copy", and
content and output paths as relative to the collection, and
`site/static/structures/` as the collection's `static/structures/` (in
tests, the demo's). Archive performs
that rewrite in every main spec (tasks.md section 6).

### D12 Test harness

`make_sandbox` creates, under one directory whose name contains a space,
an application copy (`tools/`, `site/`, `templates/`, with `.emacs-batch/`
and `.tools/` linked from the real checkout) and a collection copy of
`examples/demo/`. `Sandbox.root` is the collection, `Sandbox.app` the
application; `Sandbox.build` runs `<app>/tools/orgsyndb -C <root>` from a
third, unrelated working directory. The fish syntax test becomes
`py_compile` for the program and `sh -n` for the hook.

## Risks / Trade-offs

- **Two repositories can drift.** A collection may be built by an
  application version whose schema rejects it. → The validator runs before
  every build, and `format` catches layout changes. Pinning the application
  version per collection (a submodule or a recorded commit) is left to the
  deployment change.
- **The application checkout must be writable** for its tool caches. →
  Unchanged from today; moving caches to `$XDG_CACHE_HOME` is a separate
  change.
- **IDs of demo procedures deleted before the move are invisible** to
  next-ID. → Sample data only; the real collection starts its own history.
- **Breaking command change.** → One owner and a co-worker; the README
  documents the new commands and the move.

## Migration Plan

1. Build the demo: `tools/orgsyndb -C examples/demo build`.
2. Create the private collection: `tools/orgsyndb init ~/orgsyndb-data`,
   `git init` it, add procedures, and build with `-C` or from inside it.
3. Optionally enable the hook there:
   `git config core.hooksPath <app>/tools/hooks`.

Rollback is checking out the previous application commit; a collection's
files are what the old layout held under `org/`, `md/` and
`site/static/`.

## Open Questions

None blocking. Deployment and editing are for later changes.
