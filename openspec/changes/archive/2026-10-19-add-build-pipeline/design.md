## Context

This is change 2 of 3. Change 1 (`add-procedure-schema`, archived) fixed the
schema and the validator. Its specs, `openspec/specs/procedure-schema` and
`openspec/specs/procedure-validation`, are frozen for this change. Every
decision below conforms to them, and none needs a MODIFIED delta (see
"Conformance to the frozen schema").

Change 1 left these obligations to this change:

- `export.el` parses `#+CREATED` and `#+LAST_MODIFIED` itself, because
  Org 9.7.11's parser drops seconds. It emits `date` and `lastmod` with the
  Europe/Berlin offset, maps `#+AI_MODEL`, and disables `author`.
- The export keeps itself fresh and leaves no orphans. The validator's
  cross-check catches only a missing export and a `date`, `lastmod` or
  `ai_model` mismatch.
- Hugo mounts exactly the two validated content roots into the
  `procedures` section, with the `/procedures/:slug/` permalink.
- `orgsyndb new` fills the template placeholders: `OSDB-0000`,
  `osdb-0000`, the timestamp lines and `#+AI_MODEL`.

Machine facts (Fedora 44):

- Installed: Hugo 0.162.1 (Fedora, extended), WeasyPrint 70.0, Emacs 30.2
  with native compilation and Org 9.7.11, Python 3.14, pytest
  8.4, and git.
- Caddy is not installed; 2.10.2 is in the repositories.
- Node 22 is present but must not become a dependency.
- The owner's Emacs configuration lives in `~/.config/emacs` and must stay
  untouched.

Stakeholders:

- the owner, who authors in Org and runs builds;
- the co-worker, who authors in Markdown, runs `new`, `validate` and
  `serve`, and knows no git, Org or Hugo;
- change 3, which replaces the layouts and adds samples.

## Goals / Non-Goals

**Goals:**

- One command (`tools/orgsyndb build`) that goes from a fresh clone to
  an indexed static site with no manual steps beyond the printed `dnf`
  line.
- An export that is deterministic, isolated from the owner's Emacs, and
  pinned to exact upstream commits.
- Logic that can be tested without Emacs, Hugo or the network, kept apart
  from the thin adapters that call those tools.
- Interfaces exact enough for change 3: export directory, mounts, layout
  contract, Pagefind bundle location, serve URL and ID numbering.

**Non-Goals:**

- The theme, CSS, search UI and filters, the print stylesheet, the sample
  banner, precursor and used-in links, the remaining samples, and the
  structure images. These belong to change 3.
- Acceptance checks 3, 4 and 5, and the visual half of 7 (headers, footers,
  clipping). They depend on change 3's layouts.
- Incremental export.
- Deploying anything.
- Documents a person reads. The doc writer writes those from this change
  after implementation.

## Decisions

### D1. Where code lives: a thin entry point over a Python core

- `tools/orgsyndb` is the single user-facing entry point. It parses
  subcommands, resolves the repository, sets the environment, checks tools,
  orders steps and prints progress.
- `tools/pipeline.py` is a stdlib-only Python 3.14 module with a small CLI.
  `orgsyndb` calls it for every decision that has a right answer worth
  testing:
  - the export plan;
  - the recoverable replacement of the export directory (D4);
  - next-ID allocation;
  - slug derivation;
  - template filling;
  - PDF job naming and the WeasyPrint loop;
  - Pagefind download and verification.

  It follows the conventions of `validate.py` (design D12 of change 1):
  shebang, PEP 723 block, annotations, 79 columns, contract docstrings,
  and pure functions kept apart from I/O.
- `tools/export.el` is the only Emacs Lisp. It receives a finished plan,
  so it computes no timestamp and parses no keyword.
- `pipeline.py` imports `validate.py`'s helpers (`discover`,
  `org_keywords`, `parse_org_timestamp`, `lint_org` and `load_zone`)
  instead of re-implementing them. The export and the validator then
  cannot disagree about which files are procedures, or about what a
  timestamp means. These helpers are not part of the validator's specified interface.
  The implementer may adjust them, provided the validator suite stays
  green.

The `pipeline.py` interface the tests are written against is below. Each
function is pure unless marked otherwise.

| Function | Contract |
|---|---|
| `slugify(title: str) -> str` | ASCII short slug matching `[a-z0-9]+(-[a-z0-9]+)*`, at most 40 characters. Raises `ValueError` when no letter or digit survives. |
| `next_id(names: Iterable[str]) -> str` | `OSDB-NNNN`, one above the highest number found in a name beginning `OSDB-NNNN` (case-insensitive), or `OSDB-0001` when there is none. Raises `ValueError` when 9999 is taken. |
| `org_timestamp(moment: datetime) -> str` | An aware instant as Berlin wall-clock time, `[YYYY-MM-DD Day hh:mm:ss]`, with the English weekday whatever the locale. |
| `rfc3339(moment: datetime) -> str` | An aware instant in Berlin, `YYYY-MM-DDThh:mm:ss+HH:MM`. |
| `export_instants(created, last_modified) -> tuple[datetime, datetime]` | Takes two non-empty, earliest-first lists of instants (as `parse_org_timestamp` returns them) and returns `(date, lastmod)` under the rule in D3. |
| `fill_template(text, kind, ident, title, now, ai_model) -> str` | The `new` substitution in D11. `kind` is `"org"` or `"md"`. `ai_model` is `None` for a human author. Raises `ValueError` when an anchor line is missing or repeated. |
| `recover_export(build: Path) -> None` | (file I/O) Repairs what a crashed replacement left in `build`, as in D4. |
| `replace_export(build: Path, rename=os.rename, remove=shutil.rmtree) -> None` | (file I/O) Replaces `build/export` with `build/.export-staging` as in D4. `rename` and `remove` are injectable so tests can make any step fail. |
| `pdf_jobs(files, public, pdf_dir) -> list[PdfJob]` | Takes `(content path, front matter)` pairs and returns `PdfJob(html, pdf)` pairs under the rule in D10, sorted by PDF name. |
| `install_pagefind(tarball, tar_sha256, bin_sha256, dest) -> Path` | (file I/O) Verifies and extracts the binary as in D8. Raises `PagefindError` naming the expected and actual hash. |

`replace_export` takes no plan. The check that the staging directory holds
exactly the planned files is made by the `install-export BUILD` subcommand,
which reads `BUILD/export-plan.json` and calls `replace_export` only when
the check passes.

CLI subcommands: `export-plan`, `recover-export`, `install-export`,
`next-id`, `new`, `pdf`, `ensure-pagefind`. Their arguments are given in the specs. They exit 0 on
success, 1 on failure and 2 on usage errors, and write errors to stderr as
`pipeline.py: error: <message>`.

*Rejected alternatives:*

- *Timestamp logic in Elisp.* Testing it would need Emacs, and it would be
  a second parser of the keyword format beside `validate.py`'s, written in
  a second language.

### D2. Pinning ox-hugo: `package-vc-install` at upstream commits

`export.el` installs two packages into `<repo>/.emacs-batch/elpa/`, each at
a pinned commit and each only if missing:

| Package | Upstream | Commit | Corresponds to |
|---|---|---|---|
| tomelr | `https://github.com/kaushalmodi/tomelr` | `670e0a08f625175fd80137cf69e799619bf8a381` | tag `v0.4.3`, the GNU ELPA 0.4.3 release |
| ox-hugo | `https://github.com/kaushalmodi/ox-hugo` | `b7dc44dc28911b9d8e3055a18deac16c3b560b03` | MELPA `20251206.1738`, whose `ox-hugo-pkg.el` records this `:commit` |

Each package is installed with `(package-vc-install (list NAME :url URL)
COMMIT)`, with `package-archives` set to nil and tomelr installed before
ox-hugo. ox-hugo's `Package-Requires` (`emacs`, `tomelr`) is then satisfied
locally, so no archive is consulted. On every run, `export.el` compares each
checkout's `HEAD` with its pin. A mismatch fails the export, naming the
package, both commits, and the remedy `tools/orgsyndb clean --all`.

**Isolation.** These are set at the top of `export.el`, before
`(require 'package)`:

- `user-emacs-directory` → `<repo>/.emacs-batch/`;
- `package-user-dir` → `<repo>/.emacs-batch/elpa`;
- `package-gnupghome-dir` → `<repo>/.emacs-batch/elpa/gnupg`;
- `temporary-file-directory` → `<repo>/build/tmp/`, created if missing.
  The environment variable `TMPDIR` is set to the same directory, for
  subprocesses such as git.

Setting them before `(require 'package)` is load-bearing. `package-user-dir`
is an autoloaded defcustom, so its default is fixed at startup from the
real user directory, and `package-gnupghome-dir` is derived from it when
package.el loads. Setting `package-user-dir` only after the require put a
GnuPG trust database into `~/.config/emacs/elpa/gnupg/` (verified; see
Verification).

The temporary directory matters for the same reason. When Org loads under
`emacs -Q`, `org-persist` creates `org-persist-XXXXXX` in
`temporary-file-directory`, which is inherited from `TMPDIR` (on the
owner's machine a directory under `~/.cache/`). It deletes the directory
again at exit. So a check made after the run cannot see the write, but the
write happened (verified). `build/tmp/` is gitignored with the rest of
`build/`, and each export empties it first. As a precaution, the implementer also points
`native-comp-eln-load-path` at the repo-local directory and disables JIT
native compilation. That has not been shown necessary: the verified run
wrote no `eln-cache` anywhere.

**Cost.** The first run clones both repositories (about 17 MB) and
byte-compiles them, which took about 20 s. ox-hugo's `test/` files emit
harmless compile errors. `orgsyndb` therefore prints one line before a
bootstrap and sends Emacs's output to `build/export.log`, which it prints
only on failure. The bootstrap needs `git` and network access to GitHub.

*Rejected alternatives:*

- *package.el from GNU ELPA and MELPA, recording the installed versions.*
  MELPA serves only its latest build, so a fresh clone gets whatever
  ox-hugo is current that day. Recording versions detects drift but cannot
  prevent it, and failing on drift would break a fresh clone as soon as
  upstream moves.
- *Vendored tarballs committed to the repository.* Even trimmed to their
  `.el` files the two packages are about 0.4 MB of third-party code; the
  full ox-hugo tree without `.git` is 7.2 MB (measured). That weight lands
  in every clone, and updating a pin becomes a manual re-vendoring. Its one advantage, working offline on a fresh clone,
  does not apply: Pagefind needs the network on first build anyway.
- *GitHub archive tarballs with a SHA-256 pin.* GitHub does not guarantee
  that generated archives keep stable bytes. A git commit hash is already a
  content address.
- *MELPA Stable.* It offers a "latest stable" version, not a pin, and is
  not the build the probe verified.

### D3. Export plan and the timestamp rule

The export runs in three steps:

1. `pipeline.py export-plan ORG_ROOT PLAN_JSON` takes exactly the
   entries that `validate.discover(ORG_ROOT, ".org")` returns with no
   problem attached, the files the validator examines as Org procedures,
   and runs `lint_org` on each. The following are never planned and so
   never exported:
   - dotfiles, such as the Emacs lock symlink `.#OSDB-0001-x.org`;
   - subdirectories;
   - files that do not end in `.org`.

   The validator reports the subdirectories and stray files when it runs
   next.
   - If any file has a lint error, it prints the validator-format lines
     (`<path>:<field>: error: <message>`) to stderr, writes no plan, and
     exits 1.
   - Otherwise it writes a JSON array sorted by file name. Each element has
     the following keys:
     - `source`: absolute path;
     - `stem`: file name without `.org`;
     - `date` and `lastmod`: RFC 3339 strings;
     - `ai_model`: the identifier, or `null` for `none`.
2. `emacs -Q --batch -l tools/export.el PLAN_JSON STAGING_DIR` exports each
   entry. For each one it:
   - copies the source into a temporary buffer with
     `insert-file-contents`, with `default-directory` set to the source's
     directory;
   - prepends `#+DATE:`, `#+HUGO_LASTMOD:`, `#+EXPORT_FILE_NAME: <stem>`
     and, when `ai_model` is non-null,
     `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model "<id>"`;
   - seeds Emacs's random number generator with `(random "<stem>")`
     (D6);
   - calls `org-hugo-export-to-md` and writes the result as
     `STAGING_DIR/<stem>.md`.

   Any error exits non-zero after printing `export.el: <source>:
   <message>`.
3. `pipeline.py install-export` installs the staging directory, after `recover-export` has run at the start (D4).

**Timestamp rule.** An Org timestamp names one instant, or two in the
autumn fall-back hour. The rule is:

- `date` is the earliest instant of `#+CREATED`.
- `lastmod` is the earliest instant of `#+LAST_MODIFIED` that is not
  earlier than `date`. When none exists, it is the latest instant of
  `#+LAST_MODIFIED`.

Three consequences follow:

- Equal keywords give equal instants.
- The `OSDB-0004` fixture pair (02:50 then 02:10 on 2026-10-25) exports as
  `+02:00`, then `+01:00`.
- An export of any source that passes the lint satisfies the
  authoritative `lastmod >= date` check. The lint accepts exactly the pairs
  for which such a choice exists (change 1, D2).

Both chosen offsets are Berlin offsets in force at those instants, so the
validator's cross-check accepts them.

*Rejected alternatives:*

- *`date` earliest, `lastmod` latest.* Equal keywords in the ambiguous
  hour would export an hour apart.
- *Always the first occurrence (`fold=0`).* This exports the valid fixture
  pair out of order, and the build would fail on a source the lint
  accepts.
- *One Emacs process per file, with dates passed as arguments.* Emacs
  start-up would dominate, and paths would travel as argv strings instead
  of JSON.

### D4. Export directory, freshness and recoverable replacement

Three sibling directories under `build/` take part:

- `build/export/`: the live export, which Hugo and the validator read;
- `build/.export-staging/`: the export being written;
- `build/.export-previous/`: the backup of the live export during a
  replacement.

`orgsyndb export` runs these steps:

1. **Recover** (`pipeline.py recover-export <repo>/build`). This repairs
   whatever an interrupted run left behind:
   - If `.export-previous/` exists and `export/` does not, the run crashed
     between the two renames below. `.export-previous/` is renamed back to
     `export/`.
   - If both exist, the run crashed after the second rename. The new export
     is live, so `.export-previous/` is deleted.
   - Any `.export-staging/` is deleted.
   - `build/tmp/` is emptied.
2. **Stage.** Create an empty `.export-staging/`, write the plan to
   `build/export-plan.json`, and run `export.el` into the staging
   directory.
3. **Install** (`pipeline.py install-export <repo>/build`). First check that
   the staging directory holds exactly the planned `<stem>.md` files. Then:
   1. If `export/` exists, rename it to `.export-previous/`.
   2. Rename `.export-staging/` to `export/`. If this rename fails, rename
      `.export-previous/` back to `export/` and fail. If that restore also
      fails, fail with a message saying that the next run will recover.
   3. Delete `.export-previous/`. If the delete fails, the new export is
      already live, so this is only a warning, and the next run's recovery
      removes the backup.

Each step is a `rename(2)` within one directory, which is atomic on one
filesystem. At every moment a complete export therefore exists as
`export/` or as `.export-previous/`, and the recovery step puts it back in
place. `replace_export` takes the rename and remove functions as
parameters, so a unit test can make any rename, or the final delete,
fail. That covers
failure during replacement, not only before it.

Further rules:

- When there are no Org sources, `build/export/` still exists, and it is
  empty. A missing mount source is silently ignored by Hugo (verified), and
  the validator rejects a root that is not a directory.
- Any failure in steps 2 or 3 leaves `build/export/` with its previous
  contents, and `build` and `validate` stop.
- Every run re-exports every Org file. The output is byte-identical when
  the sources are unchanged, given three things:
  - the dates are injected;
  - `org-hugo-auto-set-lastmod` stays nil;
  - Org's reference IDs are made deterministic (D6).

  Without the third, a named element such as `#+name: observation` gets a
  random `<a id="org…">` anchor on every run (reproduced with the pinned
  checkout).

*Rejected alternatives:*

- *Exporting in place, then deleting exports whose stem has no source.*
  This needs more logic, and a failure halfway leaves a mixed directory.
- *Exporting only sources newer than their export.* Git checkouts reset
  mtimes. A change to `export.el` or to the pin would not trigger a
  re-export. The saving is about a second for six files.
- *ox-hugo's default output into `site/content/`.* That is the committed
  tree, which brief §3 forbids.
- *Removing `build/export/` and then renaming the staging directory into
  place.* A crash or a failed rename between the two steps leaves no export
  at all, or a partial one.
- *Swapping through a symlink (`build/export` → `export.N`).* Replacing a
  symlink atomically needs a rename of a second link, so it still needs
  crash recovery for the leftover targets. Hugo's handling of a symlinked
  mount source was not tested, so it would add an unverified dependency.

### D5. The tomelr table-order guard

`export.el` adds `:filter-args` advice to `org-hugo--gen-front-matter`.
The advice stably moves every entry whose value satisfies
`tomelr-toml-table-p` after all other entries, and keeps the relative order
within each group. tomelr then writes the `[product]` header last, so no
later key can fall inside it.

ox-hugo builds this list itself; its fixed leading keys come before the
custom keys. Before exporting, `export.el` checks that both
`org-hugo--gen-front-matter` and `tomelr-toml-table-p` are bound, and fails
loudly otherwise. Advising an internal (`--`) function is acceptable only
because the commit is pinned. The check turns a future rename into an
error instead of a silent loss of the guard.

The Org template keeps `product` on its last custom-front-matter line, as
the frozen "Org template" requirement demands. With the guard, that order is
belt and braces rather than the only defence.

*Rejected alternatives:*

- *Relying on source order alone.* One misplaced line in an owner's file
  would nest every later key in `product`. For the optional keys
  (`precursors`, `references`) this surfaces only as `product.<key>:
  unknown field` warnings, so the build would publish a procedure without
  its precursor links.
- *A post-export TOML check that fails the export.* It detects the bug but
  does not fix it, and it must guess which keys belong in `product`.
- *Patching or forking tomelr.* That is a maintained fork for a one-line
  ordering problem.

### D6. Body export options, including `$` and LaTeX

`export.el` binds the following:

| Setting | Value | Why |
|---|---|---|
| `org-export-with-author` | nil | The schema forbids `author`. |
| `org-html-with-latex` | `verbatim` | LaTeX fragments pass through as the author typed them. |
| `org-export-with-sub-superscripts` | `'{}` | Only `H_{2}O` and `10^{-3}` become `<sub>`/`<sup>`. |
| `org-export-use-babel` | nil | Code blocks never run at export. |
| `enable-local-variables` | nil | File-local variables in a source cannot change the export. |
| `org-hugo-base-dir`, `org-hugo-section` | staging | Sources set neither (frozen template rule). |
| random seed | `(random "<stem>")` before each source | Org's reference IDs become a function of the file name (below). |

The environment is `TZ=Europe/Berlin` and `LC_TIME=C`, set by `orgsyndb`
for every child process.

**Deterministic reference IDs.** Org 9.7.11's `org-export-new-reference`
draws each internal reference from `(random #x10000000)`. ox-hugo writes
them as `<a id="org…">` anchors, for example for a `#+name:` element, so
two runs gave different bytes (reproduced). Seeding the generator with the
source's stem immediately before each export makes the sequence a function
of the stem and of the document's own structure. Three probe results
support this (verified):
- two runs gave identical files;
- exporting two sources in either order in one Emacs process gave the
  same bytes;
- each file was identical to its single-file export.

An anchor changes only when the references in that document change, or
when an Emacs upgrade changes the generator. `build/` is gitignored, so
neither produces a committed diff.

*Rejected alternatives for reference IDs:*

- *Seeding from a hash of the file content.* Every edit would renumber
  every anchor in the file, so an external link to an anchor would break on
  any change.
- *Overriding `org-export-new-reference` with a counter.* That redefines a
  core Org function, which `export.el` would then have to track across
  Org versions. A seed changes no code.
- *Stripping the anchors after export.* That would break `[[observation]]`
  links inside the document.

ox-hugo's back end derives from `ox-html`, whose `:with-latex` option is
bound to `org-html-with-latex`. Setting `org-export-with-latex` therefore
had no effect (verified). With `verbatim`:

- `$x$` exports as `$x$`.
- `\(y^2\)` exports as `\\(y^2\\)`, which Goldmark renders as the literal
  text `\(y^2\)`.
- `\alpha` becomes the entity `α`.

No math renderer is configured or loaded, and Goldmark's passthrough
extension stays off. A source line like "costs $5 and $10" renders
unchanged.

*Rejected alternatives for LaTeX:*

- *The default (`t`/`mathjax`).* It emits MathJax delimiters for a renderer
  that will never load. The output is the same as `verbatim` for `\(…\)`
  but rewrites `$x$`.
- *`nil`.* It deletes the fragments from the output entirely (verified), so
  content is silently lost.
- *MathJax or KaTeX served locally.* No math rendering is wanted, and it
  would add a vendored JavaScript dependency.

*Rejected alternatives for sub/superscripts:*

- *`t`.* It turns `yield_percent` into `yield<sub>percent</sub>` and
  mangles `CO_2`-style plain text.
- *`nil`.* It loses the chemistry subscripts that the template's braced
  form provides.

### D7. Hugo configuration and the mounts

`site/hugo.toml` holds the following:

```toml
baseURL = "/"
title = "OrgSynDB"
locale = "en"
publishDir = "../public"
relativeURLs = true
buildFuture = true
buildExpired = true
disableKinds = ["rss", "sitemap"]

[taxonomies]
author = "authors"
reaction_type = "reaction_types"
tag = "tags"

[permalinks.page]
procedures = "/procedures/:slug/"

[markup.goldmark.renderer]
unsafe = true

[[module.mounts]]
source = "content"
target = "content"

[[module.mounts]]
source = "../build/export"
target = "content/procedures"
files = ["/OSDB-*.md"]

[[module.mounts]]
source = "../md/procedures"
target = "content/procedures"
files = ["/OSDB-*.md"]
```

Each setting has a reason:

- **Restated `content` mount.** Declaring any `content` mount drops
  Hugo's default one. Without the restatement, `site/content/_index.md` was
  ignored (verified).
- **`files = ["/OSDB-*.md"]`.** This publishes exactly the top-level files
  that the validator examines as procedures. Verified exclusions:
  - a nested `sub/OSDB-0009-*.md`;
  - `notes.txt`, which without a filter is published as
    `/procedures/notes.txt`;
  - `_index.md`, which without a filter replaces the section page;
  - an Emacs lock symlink `.#OSDB-…md`.

  Every name the filter excludes is either one the validator skips
  silently (`_index.md`, dotfiles) or one it reports, as an error for a
  subdirectory or a bad file name, or as an "ignored" warning for
  non-`.md` files. So nothing the validator has not checked reaches the
  site.
- **`disableKinds = ["rss", "sitemap"]`.** The built-in RSS and sitemap
  templates write `http://www.w3.org/2005/Atom` and
  `http://www.sitemaps.org/…` namespace URLs into `index.xml` and
  `sitemap.xml` (verified). An internal static site needs neither. Taxonomy
  and term pages stay enabled for change 3.
- **`relativeURLs = true`.** Hugo rewrites root-relative `href`/`src`
  attributes in HTML to relative ones. WeasyPrint renders
  `public/…/index.html` from a `file:` path, where `/css/x.css` would
  resolve to the filesystem root. With the rewrite, the stylesheet
  resolved, including through a directory name with a space (verified).
  CSS `url()` values are not rewritten (assumed from Hugo's documentation,
  not verified), so change 3 writes them relative.
- **`markup.goldmark.renderer.unsafe = true`.** ox-hugo emits inline HTML
  (`<sub>`, `<sup>`). Without this setting Hugo replaced it with
  `<!-- raw HTML omitted -->` (verified). Authors are trusted in-house
  staff, so raw HTML in Markdown sources is accepted.
- **`publishDir = "../public"`.** The site goes to the repository root's
  `public/`, as brief §4 lays out, and a bare `hugo` run inside `site/`
  writes to the same place (verified).
- **`locale`.** `languageCode` is deprecated since Hugo 0.158 and warns on
  every build (verified).
- **`buildFuture = true`.** Hugo omits pages dated in the future by
  default. A valid procedure whose `date` (or a stray `publishDate`) lies
  ahead, for example from a clock mistake or a planned entry, would
  silently vanish from the site, the search index and the PDF jobs. It
  would also break `pdf`, whose jobs come from the content files (D10).
  With the default, a page dated 2099 was not published; with the flag set
  it was (verified).
- **`buildExpired = true`.** The schema has no expiry field, but
  `expiryDate` is a key Hugo honours. A Markdown author who adds it gets
  only an `unknown field` warning, and by default Hugo then drops the page
  once the date passes (verified with an `expiryDate` in the past). With
  the flag set, publication never depends on a date, so the set of pages
  Hugo publishes is exactly the set the validator passed. Retiring a
  procedure is done with `status = "retired"`.

`build` runs `hugo --source "<repo>/site" --minify`. Two builds of the same
input produced identical trees (verified with `diff -r`).

*Rejected alternatives:*

- *`files = ["/*.md", "! /_index.md"]`.* In Hugo 0.162.1 the first
  matching pattern wins, so the exclusion after the inclusion never
  applied, and the section page was replaced (verified). Writing the
  exclusion first works, but stays fragile to edit.
- *Copying both trees into `site/content/procedures/` at build time.*
  Change 1 (D3) rejected this: the page's source path would no longer be
  the file the author edits.
- *Symlinking the two trees into `site/content/`.* Hugo does not follow
  symlinked content directories.
- *`baseURL` set to a host name.* Every absolute URL would name a host that
  the internal site does not have.
- *Hugo's default scheduling, with the validator rejecting future dates.*
  That would change the frozen schema, and a future `date` is not wrong
  data. Hugo's scheduling serves blogs, not a reference collection.
- *Leaving `buildExpired` at its default because no schema field sets
  it.* The validator only warns on `expiryDate`, so that default leaves a
  route by which a validated page disappears.

### D8. Pagefind acquisition and indexing

`pipeline.py ensure-pagefind --tools-dir <repo>/.tools` prints the path of
a verified binary, fetching it first when needed. The pinned constants are:

- version `1.5.2`;
- URL
  `https://github.com/Pagefind/pagefind/releases/download/v1.5.2/pagefind-v1.5.2-x86_64-unknown-linux-musl.tar.gz`;
- tarball SHA-256
  `afb824a9e7f64905a934900481cea5be679c03975e527329e0e5e6cc70f5feda`;
- binary SHA-256
  `c4b86009ce5420dc2a1748ab2705bef6ba730ed883f684fd52ef6008bd600532`.

The procedure is as follows:

1. If `.tools/pagefind-1.5.2/pagefind` exists and its SHA-256 equals the
   binary pin, print its path. Hashing 10 MB takes milliseconds.
2. Otherwise, delete it, then download the tarball with `urllib` into a
   fresh, empty `.tools/pagefind-1.5.2/download/`.
3. Verify the tarball hash. Extract only the member named `pagefind`, which
   must be a regular file, without `tarfile`'s general extraction. Verify
   the binary hash, `chmod 0755`, and rename it into place.
4. Delete the download directory. Any mismatch or network error deletes
   whatever was written and exits 1, naming the URL, or the expected and
   actual hashes.

`build` then runs `<pagefind> --site "<repo>/public"`. The bundle lands in
`public/pagefind/`. Because the layouts mark only procedure bodies with
`data-pagefind-body`, Pagefind skips every other page (verified: "Ignoring
pages without this tag"). `pagefind-entry.json` records `page_count`.

The hashes are pinned in the repository rather than taken from the
release's `.sha256` file at run time. A checksum fetched from the same
origin shows that the download is intact, but not that it is the binary
that was reviewed.

*Rejected alternatives:*

- *The PyPI `pagefind` package.* It needs pip, which the owner excluded.
- *npm.* It needs Node.
- *Downloading on every build.* It is slow and needs the network every
  time.

### D9. `serve`: Python's `http.server` on 127.0.0.1:8000

`serve [--port N]` runs `build`, then:

```
python3 -m http.server --bind 127.0.0.1 --directory "<repo>/public" <port>
```

Before the server starts, it prints the line `serving
http://127.0.0.1:<port>/ (Ctrl-C to stop)`. It prints the line once
`http.server` reports that it has bound the port, so a client that waits
for the line is never refused a connection. The default port is 8000. Pages,
`pagefind.js`, `pagefind-entry.json` and the `.pagefind` WASM files were all
served with status 200. A Pagefind search run against this server returned
the expected page (verified; see Verification).

*Rejected alternatives:*

- *`pagefind --serve`.* It binds the fixed address `127.0.0.1:1414` with no
  option to change it, so a busy port is unrecoverable. It also re-indexes
  and serves the Pagefind playground (verified).
- *`hugo server`.* It renders into memory and does not serve the Pagefind
  index (brief §7.1).
- *`caddy file-server`.* It adds an optional package as a requirement for
  previewing. Caddy stays the deploy example (D15).
- *Binding `0.0.0.0`.* It would expose confidential procedures to the
  local network.

### D10. `pdf`: a subcommand, named after the source file

`pdf` runs `build`, deletes `pdf/`, and calls `pipeline.py pdf --public
"<repo>/public" --pdf-dir "<repo>/pdf" build/export md/procedures`.

- **Jobs.** For every procedure content file in those roots, the HTML input
  is `public/procedures/<front-matter slug>/index.html` and the output is
  `pdf/<content file stem>.pdf`, for example
  `pdf/OSDB-0002-aspirin.pdf`. Validation has already guaranteed that the
  stem begins with `id` and that `slug` equals `id` lowercased, so the name
  is `OSDB-NNNN-short-slug.pdf`, as brief §7.1 asks. A missing HTML file is
  an error naming the expected path.
- **Rendering.** Each job runs
  `weasyprint --allowed-protocols file <html> <pdf>` with
  `PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning"`. That
  filter silenced pyphen's warning while leaving other warnings visible
  (verified).
- **Failure.** A job fails when WeasyPrint exits non-zero or writes a line
  beginning `ERROR:`. With only `file:` allowed, an `https:` stylesheet is
  refused with such a line, but WeasyPrint still exits 0 (verified). A
  failed job's partial PDF is deleted, and the remaining jobs still run.
  `pdf` exits 1 when any job failed.
- **Progress.** It prints one `pdf: <name>` line per file and a final count.
- **Output.** WeasyPrint's default page is A4 (595.28 × 841.89 pt,
  verified). Its PDFs embed creation metadata, so repeated runs are not
  byte-identical (verified). Nothing requires them to be.

*Rejected alternatives:*

- *Naming from a `<meta>` tag in the HTML.* It would impose a markup
  obligation on change 3's layouts for something the content files already
  determine.
- *`<slug>.pdf`.* That gives `osdb-0002.pdf`, which is not the name the
  brief asks for.
- *Rendering from a running HTTP server.* It needs server lifecycle
  management inside a batch job, which `relativeURLs` makes unnecessary.
- *Rendering whatever HTML is already in `public/`.* It could print stale
  pages, or nothing at all on a fresh clone.

### D11. `new`: next ID, slug, template filling

`tools/orgsyndb new [--md] [--ai-model ID] TITLE...` calls
`pipeline.py new --repo "<repo>" [--md] [--ai-model ID] TITLE`. It joins the
title words with single spaces and trims the result.

**Next ID.** The candidate names are:

- the top-level entries of `org/procedures/`, `md/procedures/` and
  `build/export/`;
- the base names that `git -C <repo> log --all --no-renames --format=
  --name-only -- org/procedures md/procedures` reports.

`next_id` returns one more than the highest `OSDB-NNNN` among them. Gaps
are never filled, because a gap may be a deleted ID. When `git` is missing
or the directory is not a repository, `new` prints a warning to stderr and
uses the trees alone. When `git rev-parse --is-shallow-repository` reports
`true`, `new` still scans the history it has, and warns that IDs deleted
before the shallow boundary are invisible.

**What "never reused" can and cannot mean.** Without a registry, the only
memory of a deleted procedure is the git history. So `new` never reuses an
ID that is present now, or that was ever committed on any ref this clone
has fetched. It cannot see:

- a file that was created and deleted without ever being committed;
- commits on another clone that have not been fetched, such as the
  co-worker's unpushed work;
- history that was rewritten away;
- history beyond the boundary of a shallow clone (`git clone --depth N`),
  whose earlier commits are not present locally. `new` warns in this
  case.

If two people allocate the same ID in parallel, the clash surfaces as the
validator's duplicate-ID error once both files meet in one tree. The
export directory is scanned too. That costs nothing, and it also covers an
Org file deleted after its last export.

**Slug.** `slugify` works in these steps:

1. Apply NFKD, drop non-ASCII, and lowercase.
2. Replace each run of characters other than `[a-z0-9]` with `-`, and trim
   `-` from both ends.
3. Cut to at most 40 characters, at the last `-` within the limit when
   there is one, and trim `-` again.

An empty result is a usage error ("the title needs at least one letter or
digit"). Examples: "4-tert-Butylcyclohexanol" gives
`4-tert-butylcyclohexanol`, "(E)-Chalcone" gives `e-chalcone`, and
"Salicylic acid" gives `salicylic-acid`.

**Filling.** `fill_template` follows change 1's D8 exactly and adds the
title:

- Every `OSDB-0000` becomes the ID, and every `osdb-0000` its lowercase
  form.
- **Org.** The values of the `#+TITLE:`, `#+CREATED:`, `#+LAST_MODIFIED:`
  and `#+AI_MODEL:` lines, matched case-insensitively and each exactly
  once, become:
  - the title;
  - `org_timestamp(now)` for both timestamps;
  - `none`, or the `--ai-model` value.
- **Markdown.** Inside the front matter:
  - the `title = …` line becomes the title as a TOML basic string, so
    quotes and backslashes are escaped and the value round-trips through
    `tomllib`;
  - the `date = …` and `lastmod = …` lines become `rfc3339(now)`;
  - with `--ai-model`, the commented line `# ai_model = …` becomes
    `ai_model = "<ID>"`. Without it, that line stays commented out.
- `now` is the current instant in Europe/Berlin, truncated to whole
  seconds. Tests pass it with `--now`.
- Weekday names come from a fixed English table, never from `strftime`.
  Under the brief's `LC_TIME=C` the two agree anyway.
- The `--ai-model` value must match the schema's model-identifier pattern.
- A title containing a newline is rejected.

The file is created with exclusive creation (`open(..., "x")`) as
`<tree>/<ID>-<slug>.<ext>`, creating the tree directory when needed. `new`
then prints the repo-relative path.

*Rejected alternatives:*

- *The lowest free number.* It reuses a deleted ID whenever the gap is
  one.
- *A committed ID registry or counter file.* It causes merge conflicts
  between the two authors, adds one more file to keep in sync, and still
  misses unpushed allocations.
- *Prompting for the slug interactively.* Tests become harder, and the
  co-worker gains nothing over a title argument.

### D12. `check-deps`

`check-deps` prints one line per tool in this order:

| Tool | Fedora package | Needed by |
|---|---|---|
| `emacs` | `emacs` | export |
| `git` | `git` | export (the bootstrap, and the pin check on every run), `new` history |
| `python3` | `python3` | export plan, validate, new, pdf, Pagefind fetch |
| `hugo` | `hugo` | build |
| `weasyprint` | `weasyprint` | pdf |

The status words are as follows:

- `ok      <tool>` for a tool that is present. For `hugo` and `weasyprint`
  it adds ` (tested with 0.162.1)` or ` (tested with 70.0)` when the
  reported version differs from the tested one.
- `missing <tool>` for a required tool that is absent.
- `optional caddy`, followed by whether it is installed. Caddy is used only
  by `deploy/Caddyfile.example`, and is never counted as missing.
- `auto    pagefind 1.5.2` and `auto    ox-hugo/tomelr`, each followed by
  whether it is already cached or will be fetched on first use.

When any required tool is missing, the last line is exactly
`sudo dnf install <packages…>`, listing their packages in table order, and
the exit status is 1. Otherwise the exit status is 0. Nothing is installed
and `sudo` is never invoked.

Every other subcommand checks the tools it needs before its first step:

| Subcommand | Required tools |
|---|---|
| `export` | `emacs`, `git`, `python3` |
| `validate` without arguments | as `export` |
| `validate ARGS…` | `python3` |
| `build`, `serve` | as `export`, plus `hugo` |
| `pdf` | as `build`, plus `weasyprint` |
| `new` | `python3` (`git` is optional; without it `new` warns, D11) |
| `clean`, `check-deps`, `help` | none |

`git` is required for every export, not only the bootstrap, because every
run checks the checkouts against their pins (D2). When a tool is missing,
the subcommand prints `orgsyndb: error: <tool> not found; install it
with: sudo dnf install <package>` and exits 1, so it never stops
halfway.

*Rejected alternatives:*

- *One `sudo dnf install` line per tool.* The owner would have to copy
  several commands.
- *Installing automatically.* The brief forbids sudo.

### D13. `orgsyndb` conventions

- **Repository.** The program finds the repository from its own path,
  resolving symlinks. Before deleting anything, it refuses to run unless
  `<repo>/tools/orgsyndb` and `<repo>/site/hugo.toml` exist.
- **Working directory.** Child tools run with the repository as their
  working directory and get repo-relative paths, so validator lines read
  `md/procedures/OSDB-0002-aspirin.md:…`. The one exception is
  `validate ARGS…` (D14).
- **Environment.** `TZ=Europe/Berlin` and `LC_TIME=C` are exported for
  every child process.
- **Output and exit status.**
  - Each step prints `==> <step>…` to stdout.
  - Errors go to stderr as `orgsyndb: error: <message>`.
  - The exit status is 0 on success, 1 on failure, and 2 on a usage error:
    no subcommand, an unknown one, or a bad option.
  - `help`, `-h` and `--help` print the usage and exit 0.
- **Clean.** `clean` removes `build/`, `public/`, `pdf/`,
  `site/.hugo_build.lock` and `site/resources/`. `clean --all` also removes
  `.emacs-batch/` and `.tools/`. Nothing else is touched, and cleaning an
  already-clean tree succeeds.

### D14. `validate` exports first; arguments pass through

- **Without arguments,** `validate` runs `export` and then
  `validate.py --org-root org/procedures build/export md/procedures`. It
  passes the validator's output and exit status through unchanged. Its
  verdict is therefore always about the current sources. Without the
  export, an edited Org file would fail the cross-check against its stale
  export.
- **With arguments,** `validate ARGS…` forwards them verbatim to
  `validate.py`, in the caller's working directory and without exporting.
  This is how acceptance check 6 points it at fixtures:

  ```
  tools/orgsyndb validate --vocabulary tests/fixtures/reaction_types.toml \
      --static-dir tests/fixtures/static tests/fixtures/invalid/missing-title
  ```
- **`build`** runs export, then validation, then removes `public/`, then
  runs Hugo and Pagefind. Validation errors stop it before `public/` is
  touched; warnings do not.

*Rejected alternatives:*

- *`validate` never exports.* A stale export would produce cross-check
  errors that confuse authors.
- *A separate fixture subcommand.* The pytest suite already proves every
  fixture message. The pass-through gives acceptance check 6 a direct
  command without a second interface.

### D15. Pre-commit hook, Caddyfile, `.gitignore`

- **Hook.** `tools/hooks/pre-commit` is an executable `sh` script. It
  changes to `git rev-parse --show-toplevel` and runs
  `tools/orgsyndb validate`, exiting with its status. Nothing in this
  change enables it. The README will give both ways to enable it:
  `git config core.hooksPath tools/hooks`, or a symlink from
  `.git/hooks/pre-commit`.
  - It checks the working tree, not the index. A partially staged file is
    validated as it is on disk.
  - It runs on every commit. That costs about the export time, a few
    seconds.
- **Caddyfile.** `deploy/Caddyfile.example` serves a copied `public/` from
  a placeholder root with `file_server`, on the placeholder host
  `orgsyndb.internal` with `tls internal`. It has a comment header saying
  what to replace. No user or machine identifiers appear in it.
- **`.gitignore`.** The existing `__pycache__/` and `.pytest_cache/` stay.
  Anchored entries are added: `/build/`, `/public/`, `/pdf/`,
  `/.emacs-batch/`, `/.tools/`, `/site/.hugo_build.lock` and
  `/site/resources/`. Anchoring keeps a fixture directory that happens to
  be called `build` from being ignored.

*Rejected alternatives:*

- *Validating the index* by `git stash --keep-index` or a checkout into a
  temporary directory. Stash-based hooks can lose a user's unstaged work
  when they fail midway, and the temporary checkout would need its own
  export and package cache.
- *Skipping the hook when no procedure file is staged.* A change to the
  vocabulary, templates or tools can break validation too.
- *Editor patterns (`*~`, `.#*`) in `.gitignore`.* They belong in the
  owner's global ignore file.

### D16. Minimal layouts: the contract change 3 inherits

The layouts are `site/layouts/baseof.html`, `site/layouts/single.html` and
`site/layouts/list.html`. Hugo 0.162.1 uses `list.html` for home, section,
taxonomy and term pages (verified). `site/content/_index.md` gives the home
page its title.

They satisfy the following, and change 3's replacement must keep all of it:

1. Every procedure is published as
   `public/procedures/<slug>/index.html`, and its rendered body is inside
   exactly one element carrying `data-pagefind-body`.
2. No other page carries `data-pagefind-body`.
3. The heading shows the procedure's `title` and `id`.
4. Every page has `<html lang="en">`, `<meta charset="utf-8">` and a
   `<title>`.
5. No layout emits a reference that makes a browser fetch from a host
   other than the serving one: no fetching attribute or CSS `url()` with
   `http:`, `https:` or `//`. Plain `<a href>` links in body text, such as
   citations, are allowed.
6. Asset references are written root-relative (`/css/…`, `/pagefind/…`).
   `relativeURLs` rewrites them for `file:` rendering.
7. A procedure page's content does not depend on JavaScript, because
   WeasyPrint does not run it.

The current layouts add nothing beyond these: no CSS, no search box, no
metadata panel.

### D17. Seed samples

There are two seeds:

- `org/procedures/OSDB-0001-salicylic-acid.org` (Org, reaction type
  `hydrolysis`): saponification of methyl salicylate (oil of wintergreen)
  with aqueous NaOH, then acidification with HCl.
- `md/procedures/OSDB-0002-aspirin.md` (Markdown, reaction type
  `acylation`, `precursors = ["OSDB-0001"]`): acetylation of salicylic acid
  with acetic anhydride and a phosphoric acid catalyst.

Both are classic undergraduate experiments with nothing energetic,
highly toxic, controlled or dual-use. Together they form a two-step chain
across the two source trees, which exercises the cross-root precursor check
on real content.

Suggested quantities (`*` marks the limiting reagent, MW in g/mol):

| Seed | Reagent | CAS | MW | Amount | mmol | Equiv |
|---|---|---|---|---|---|---|
| 0001 | Methyl salicylate* | 119-36-8 | 152.15 | 7.61 g (6.48 mL) | 50.0 | 1.0 |
| 0001 | Sodium hydroxide | 1310-73-2 | 40.00 | 6.00 g | 150 | 3.0 |
| 0001 | Hydrochloric acid, 37 % (12.1 M) | 7647-01-0 | 36.46 | 15.0 mL | 182 | 3.6 |
| 0002 | Salicylic acid* | 69-72-7 | 138.12 | 2.76 g | 20.0 | 1.0 |
| 0002 | Acetic anhydride | 108-24-7 | 102.09 | 6.13 g (5.67 mL) | 60.0 | 3.0 |
| 0002 | Phosphoric acid, 85 % | 7664-38-2 | 97.99 | 5 drops | cat. | cat. |

The products are as follows:

- **Salicylic acid.** C7H6O3, MW 138.12, CAS `69-72-7`, SMILES
  `OC(=O)c1ccccc1O`, scale `"50 mmol"`, yield 80 % (5.52 g).
- **Acetylsalicylic acid.** C9H8O4, MW 180.16, CAS `50-78-2`, SMILES
  `CC(=O)Oc1ccccc1C(=O)O`, scale `"20 mmol"`, yield 75 % (2.70 g).

The 2.76 g that OSDB-0002 uses is less than the 5.52 g that OSDB-0001
yields. Every listed CAS number passes `validate.py`'s check-digit
function, and every MW equals the formula weight computed from IUPAC
standard atomic weights, rounded to 0.01 (both checked by script).

Other content rules:

- `references` cites the real textbook *Vogel's Textbook of Practical
  Organic Chemistry*, 5th ed. (Furniss, Hannaford, Smith, Tatchell;
  Longman, 1989) without page numbers, which could not be verified.
- The Summary says that this is sample data whose quantities are not
  experimentally verified. The visible banner is change 3's.
- Authors are fictitious (`"A. Example"`).
- `#+AI_MODEL` (Org) and `ai_model` (Markdown) name the writing model's
  exact identifier.
- The Org timestamps are the real Europe/Berlin time of writing. The
  Markdown `date` and `lastmod` are the same, with their offset.
- The seeds carry no `structure_image`, because `site/static/` arrives in
  change 3.

The quantity rules in the spec are written for every procedure tagged
`sample-data`, so change 3's samples are held to them by the same tests.
The seeds take `OSDB-0001` and `OSDB-0002`, and change 3 continues from
`OSDB-0003` via `new`. Its chain may extend this one, by citing either seed
as a precursor, or start its own.

*Rejected alternatives:*

- *Fischer esterification, then nitration.* Nitrating mixtures are
  energetic.
- *Seeding from brief §6.4's list without a link.* The precursor check
  would then never run on real exported content in this change.

### D18. Tests: layers and skips

| Layer | Needs | Skips when |
|---|---|---|
| Pure unit tests (`pipeline.py` functions, offline Pagefind verification, `replace_export`/`recover_export` with an injected failing rename and pre-built leftover directories) | Python | never |
| Configuration and content tests (parse `hugo.toml`, `.gitignore` via `git check-ignore`, Caddyfile text, seed front matter and Reagents tables) | Python, git for ignore checks | `git` missing (ignore checks only) |
| Program tests (usage/exit 2, `check-deps` under a reduced `PATH` with a recording fake `sudo`, `clean`) | Python | never |
| Integration tests (export, build, serve, pdf, hook) | Emacs and a bootstrapped `.emacs-batch/` at the pins; plus Hugo and a cached Pagefind for build and serve; plus WeasyPrint for pdf | each missing tool or cache, by name; reasons such as "ox-hugo not bootstrapped: run tools/orgsyndb export once (needs network)" |

Integration tests copy `tools/`, `site/`, `templates/`, `org/`, `md/` and
`tests/fixtures/export/` into a temporary directory whose path contains a
space. They symlink `.emacs-batch/` and `.tools/` from the real repository,
and they run `orgsyndb` with `cwd` set to a different temporary
directory. The tests then need no network, never touch the real
`build/`, `public/` or `pdf/`, and exercise quoting and any-cwd behaviour.
The pin-mismatch test copies `.emacs-batch/` instead of linking it, then
checks out the parent commit in the copy; the full clone has the history.
`serve` is tested on a free port in its own process group, which the test
kills.

**Isolation test.** The test runs the export with `HOME` set to a
temporary directory holding only an empty `.config/emacs/`, and `TMPDIR`
set to a separate temporary directory made read-only (mode 0555). The
`org-persist` directory is created at load and deleted at exit, so a check
of `TMPDIR` after the run would miss it. The read-only `TMPDIR` turns any
write into an error instead. Without the redirect, the export then fails
with `permission-denied … org-persist-` (verified); with it, the export
succeeds and `TMPDIR` stays empty (verified).

Fish behaviour verified only manually:

- `serve` interactively: Ctrl-C stops the server, and a browser search
  works.
- The first-run network bootstrap of ox-hugo, tomelr and Pagefind on a
  fresh clone.
- The hook in the owner's real repository, enabled each documented way.
- `check-deps` on a machine that really lacks packages. The automated test
  simulates this by restricting `PATH`.
- The readability of progress output in a terminal.

## Conformance to the frozen schema

- **`procedure-schema` "Org keywords map to exported front matter".**
  `date` and `lastmod` keep the wall-clock time and take a Berlin offset in
  force at that instant. D3's rule chooses between the two that the
  requirement admits. `ai_model` is omitted for `none`, `slug` comes from
  `#+HUGO_SLUG`, and there is no `author`.
- **`procedure-schema` "Org template".** It is unchanged. The guard (D5)
  adds a defence but does not relax the template rule.
- **`procedure-schema` "Slug determines the URL".** It is implemented by
  `[permalinks.page]`.
- **`procedure-validation`.** It is invoked exactly as specified, and
  file discovery matches the mount filter (D7).
- **The `valid/export` fixtures.** They were shaped from ox-hugo's source.
  Real output orders keys differently: custom keys after `draft`, and
  `ai_model` where it is injected. Its parsed values have the same shape,
  and the validator is insensitive to order. The substituted template,
  exported for real, validated with no output lines (Verification). No
  fixture correction is needed.

## Verification

Every run below was made on this machine on 2026-10-19, in throwaway
directories under the session scratchpad, never in the repository. Several
directory names contained a space on purpose.

**Hugo 0.162.1** (`hugo --minify` on a probe site with this design's
`hugo.toml`):

- The two mounts with `files = ["/OSDB-*.md"]` published only
  `procedures/osdb-0001/` (from `md/procedures`) and `procedures/osdb-0003/`
  (from `build/export`).
- Excluded were a nested `sub/OSDB-0009-*.md`, `notes.txt`, `_index.md`,
  `.gitkeep`, and a dangling `.#OSDB-…md` symlink.
- Without `files`, `/procedures/notes.txt` and `/procedures/osdb-0009/`
  were published, and `_index.md` replaced the section page.
- With `["/*.md", "! /_index.md"]` the section page was still replaced.
  With `["! /_index.md", "/*.md"]` it was not.
- Without the restated `content` mount, `site/content/_index.md` was
  ignored.
- A missing mount source was silently ignored, and the build exited 0.
- Mount sources outside the project (`../…`) work, through paths
  containing spaces.
- `.File.ContentBaseName` gives the source stem for mounted files.
- `relativeURLs = true` produced `href=../../css/p.css` on procedure pages.
- `unsafe = false` turned ox-hugo's `<sub>` into
  `<!-- raw HTML omitted -->`, and `unsafe = true` kept it.
- Without `disableKinds`, `index.xml` and `sitemap.xml` contained
  `http://www.w3.org/2005/Atom`, `http://www.sitemaps.org/schemas/sitemap/0.9`
  and `http://www.w3.org/1999/xhtml`.
- `languageCode` warned "deprecated in Hugo v0.158.0", and `locale` did
  not.
- `publishDir = "../public"` wrote to the parent's `public/`.
- `layouts/single.html`, `list.html` and `baseof.html` render pages,
  sections, home and taxonomies.
- Two consecutive builds were identical under `diff -r`.

**ox-hugo and tomelr pins:**

- A blobless clone and `git log` showed that ox-hugo commit `b7dc44dc2891`
  is dated 2025-12-06 17:38 UTC, matching MELPA's `20251206.1738`.
  MELPA's installed `ox-hugo-pkg.el` records
  `:commit "b7dc44dc28911b9d8e3055a18deac16c3b560b03"`.
- tomelr's `tomelr-pkg.el` (GNU ELPA 0.4.3) records
  `:commit "670e0a08f625175fd80137cf69e799619bf8a381"`, and tag `v0.4.3`
  exists.
- `emacs -Q --batch` with `package-vc-install (list NAME :url URL) COMMIT`
  and `package-archives` nil installed both packages. It reported "VC
  package 'ox-hugo' installed (Version 0.12.1, Revision "b7dc44dc…")", and
  `git rev-parse HEAD` in each checkout equals its pin.
- The run took about 20 s and wrote 17 MB, with compile errors from
  ox-hugo's `test/` files. A second run found both packages installed,
  so it installed nothing and fetched nothing.

**Isolation:**

- `HOME` was set to a temporary directory holding only `.config/emacs/`.
- With `package-user-dir` set after `(require 'package)`, the run created
  `~/.config/emacs/elpa/gnupg/{trustdb.gpg,pubring.kbx}`.
- With `user-emacs-directory`, `package-user-dir` and
  `package-gnupghome-dir` set first, `HOME` stayed exactly as it was
  across the install and the following run, and no `eln-cache` was
  created anywhere.

**Export:**

- Injecting `#+DATE:`, `#+HUGO_LASTMOD:`, `#+EXPORT_FILE_NAME:` and an
  `:ai_model` custom-front-matter line into a temporary-buffer copy gave
  `date = 2026-03-29T01:59:59+01:00` and
  `lastmod = 2026-10-19T17:42:05+02:00`. Both are unquoted with their
  seconds, `ai_model` was set, and no `author` was written.
- The `:filter-args` guard placed `[product]` last when the source had
  `:product` on the first custom line, with `scale`, `yield_percent` and
  `hazards` after it. `tomllib` parsed all of them at top level.
- Two exports produced byte-identical files (`cmp`).
- `org-html-with-latex` `verbatim` gave `$x$` and `\\(y^2\\)`, which Hugo
  rendered as `$x$` and `\(y^2\)`. `nil` deleted both fragments.
  `org-export-with-latex` had no effect.
- `org-export-with-sub-superscripts '{}` gave `H<sub>2</sub>O` and
  `10<sup>-3</sup>`, and left `CO_2`, `yield_percent` and `x^2` literal.
- The substituted `templates/procedure.org`, exported this way, was checked
  with `tools/validate.py --org-root <org> <export>`: "validated 2 files:
  0 errors, 0 warnings", exit 0.

**Amendment probes (after review):**

- **Reference IDs.** An Org file with `#+name: observation` before a
  paragraph was exported twice with the pinned checkout. The two runs gave
  different `<a id="org…">` values (`orga40de30` vs `org7219923`). With
  `(random "<stem>")` before each export, two runs were identical (`cmp`).
  Two sources exported in one process, in either order, gave identical
  trees (`diff -r`), equal to the single-file export.
- **org-persist.** With `TMPDIR` pointing at a probe directory,
  `directory-files` during the run showed `org-persist-XXXXXX`, gone after
  exit. With `TMPDIR` read-only and no redirect, the export exited 255 with
  `permission-denied ("Creating directory with prefix" …
  "org-persist-")`. With `temporary-file-directory` set before Org loads,
  it exited 0, `org-persist-directory` lay under the redirect, the
  read-only `TMPDIR` stayed empty, and `HOME` was unchanged. The defining
  code is `org-persist.el` around line 1310: under
  `org-persist--disable-when-emacs-Q`, it calls
  `make-temp-file "org-persist-" 'dir`.
- **Shallow clones.** A repository committed `md/procedures/OSDB-0012-old.md`
  and then deleted it. `git clone --depth 1 file://…` of it reported
  `git rev-parse --is-shallow-repository` as `true`, and its `git log --all
  --no-renames --format= --name-only -- md/procedures` was empty. The full
  repository listed the file.
- **Scheduling.** A probe site with a Markdown page dated
  `2099-01-01T10:00:00+01:00` and another with `expiryDate` in the past
  published neither by default. With `buildFuture = true` and
  `buildExpired = true` it published both.

**WeasyPrint 70.0:**

- `weasyprint --help` lists `--allowed-protocols`, `-u/--base-url`,
  `-m/--media-type` (default print), `-s`, `-q`/`-v`/`-d`, and positional
  `input output`.
- Every run prints pyphen's `pkg_resources` `UserWarning`. The `rpm`
  wrapper's shebang is `#!/usr/bin/python3 -sP`, so it honours
  `PYTHONWARNINGS`, and the targeted filter silenced the warning.
- The stylesheet loaded through a relative URL from a `file:` path
  containing a space.
- `--allowed-protocols file` refused an `https:` stylesheet with
  "ERROR: Failed to load stylesheet … disallowed protocol", and the exit
  status was 0.
- The default MediaBox was `[0 0 595.275591 841.889764]` (A4).
- Two renders of the same page differed in bytes.

**Pagefind 1.5.2:**

- The tarball SHA-256 matched the release's `.sha256`, fetched both with
  curl and with Python `urllib`, which followed the redirect. The extracted
  binary's SHA-256 is `c4b86009…0532`, and the tarball holds the single
  regular member `pagefind`.
- `--help` shows that `--serve` takes no address or port options, and the
  probe server listened on `127.0.0.1:1414`.
- Indexing reported "Found a data-pagefind-body element … Ignoring pages
  without this tag", and `pagefind-entry.json` holds `page_count`.
- The bundle's JS and CSS contain inert `http(s)://` strings (translator
  credit links, an SVG namespace). A grep for every URL would flag them,
  which is why the no-external-fetch check looks only at fetching
  attributes and CSS `url()`/`@import`.

**`http.server`:**

- `python3 -m http.server --bind 127.0.0.1 --directory "<dir with
  space>/public" 8765` served `/`, a procedure page, `pagefind.js`
  (`text/javascript`), `pagefind-entry.json` and `wasm.en.pagefind`, each
  with status 200.
- A throwaway Node script, used only as a test client, imported
  `pagefind.js` with `basePath` set to the server. `search("markdown")`
  returned the expected page.

**Unverified:**

- The Caddyfile: Caddy is not installed. If the test finds Caddy, it runs
  `caddy adapt`, and it skips otherwise.
- That CSS `url()` values are not rewritten by `relativeURLs`. This is
  Hugo documentation behaviour and matters only to change 3.
- That `package-vc-install` behaves the same on a machine whose global git
  configuration rewrites URLs or requires credentials.
- That `package-vc` in a symlinked `.emacs-batch/` works for the
  integration harness. If it does not, the harness copies the directory
  instead.
- Native-compilation side effects on a machine where JIT compilation does
  run in batch mode. Mitigated by D2's precaution.
- Headers, footers and clipping in PDFs (acceptance check 7), which depend
  on change 3's print stylesheet.
- The hook in a real commit.
- Caddy on an internal host.

## Risks / Trade-offs

- [ox-hugo's internal `org-hugo--gen-front-matter` may change upstream.] →
  The pin freezes it. The bound-function check fails loudly before export
  if a pin bump removes it.
- [First run needs network and `git`, and takes about 20 s plus the
  Pagefind download.] → `check-deps` says so. Later runs are offline.
- [`unsafe = true` lets a Markdown author embed raw HTML, including
  scripts.] → The authors are trusted in-house staff, and ox-hugo's output
  requires it. The no-external-fetch test still catches a remote `src`.
- [A bare `hugo` run before any export silently omits the Org
  procedures.] → `build` always exports first, and the README documents
  `build`, not `hugo`.
- [`new` cannot see unfetched or never-committed allocations (D11).] →
  The duplicate-ID error catches a clash when the trees meet.
- [The hook validates the working tree, not the index.] → Documented.
  The alternatives risk user data.
- [`serve` has no live reload.] → The preview is the built artefact, which
  is what the search needs. Re-run `serve` after an edit.
- [PDFs are not byte-identical between runs.] → Only the export is
  required to be idempotent, and `pdf/` is gitignored.
- [A future Emacs may change its random number generator, renumbering
  reference anchors once.] → The export directory is gitignored. Within one
  Emacs version the anchors are stable (D6).
- [A crash between the two renames briefly leaves no `build/export/`.] →
  The next export's recovery step restores the backup before doing
  anything else (D4). Nothing reads `build/export/` while an export runs.

## Open Questions

- Should `orgsyndb new` also open the new file in `$EDITOR`? Left out.
  It is easy to add later, and it would complicate tests.
- Should Pagefind's `--include-characters` cover SMILES punctuation?
  Deferred to change 3, which owns acceptance check 3.
