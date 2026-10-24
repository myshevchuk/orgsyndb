## Why

Change 1 (`add-procedure-schema`) fixed what a procedure is and shipped a
validator, but nothing yet turns Org sources into Hugo content, builds a
site, indexes it or prints it. Org procedures cannot render until an export
pipeline exists, and change 3 (`add-site-theme`) needs a working build,
search bundle and URL scheme to write its theme against. This change builds
that pipeline, with minimal layouts, and two seed procedures that exercise
it end to end.

## What Changes

- Add `tools/export.el`. It runs ox-hugo under `emacs -Q --batch` with every
  Emacs directory inside `<repo>/.emacs-batch/`, and its temporary
  directory (where Org's `org-persist` writes) inside `build/tmp/`. ox-hugo and tomelr are
  installed by `package-vc-install` at pinned upstream commits: ox-hugo
  `b7dc44dc2891` (the commit behind MELPA `20251206.1738`) and tomelr
  `670e0a08f625` (0.4.3). The export reads its dates from a plan computed in
  Python and injects them, so `date`/`lastmod` keep their seconds and get the
  Europe/Berlin offset. It maps `#+AI_MODEL`, disables `author`, and moves
  table-valued front matter last so the tomelr ordering bug cannot nest keys.
  LaTeX fragments are exported verbatim and Babel is never evaluated.
  Emacs's random generator is seeded with the source's stem before each
  export, so Org's otherwise random `org…` anchors are reproducible.
- Export into `build/export/` through a staging directory. It is
  installed by renaming the old export to a backup, renaming the staging
  directory into place, and deleting the backup, with a restore on failure.
  The next run's recovery step repairs any leftovers from a crash. The
  result is exactly one `.md` per Org source the validator examines (so
  Emacs lock files and other dotfiles are never exported), with no orphan
  files and byte-identical output on re-export.
- Add `tools/pipeline.py`, a stdlib-only helper that `orgsyndb` calls. It
  holds every piece of logic that can be tested without Emacs, Hugo or the
  network: the export plan and timestamp rules, next-ID allocation, slug
  derivation, template filling, PDF job naming, and Pagefind download
  verification, and the recoverable replacement of the export directory. It
  reuses the validator's file discovery and Org timestamp parsing.
- Add the Hugo project `site/hugo.toml`. It restates the default `content`
  mount and mounts `build/export/` and `md/procedures/` into
  `content/procedures`, limited to the files `/OSDB-*.md`. It also sets:
  - the permalink `/procedures/:slug/`;
  - `buildFuture` and `buildExpired`, so that no front-matter date hides a
    validated procedure;
  - the taxonomies `authors`, `reaction_types` and `tags`;
  - RSS and sitemap disabled;
  - `relativeURLs`;
  - Goldmark `unsafe` rendering, which ox-hugo's inline HTML needs;
  - `publishDir = "../public"`.

  Add the minimal layouts under `site/layouts/`. Each procedure becomes one
  page whose body sits inside `data-pagefind-body`.
- Pagefind 1.5.2: the standalone binary is downloaded into `.tools/` on
  first need and checked against pinned SHA-256 hashes of the tarball and of
  the binary. It indexes `public/` into `public/pagefind/`. No Node and no
  pip.
- Add `tools/orgsyndb` with the subcommands `export`, `validate`, `build`,
  `serve`, `pdf`, `new [--md]`, `clean`, `check-deps` and `help`:
  - `serve` builds the site, then serves `public/` with Python's
    `http.server` on `http://127.0.0.1:8000/`.
  - `pdf` is a subcommand. It builds, then renders
    each procedure page to `pdf/<source stem>.pdf` with WeasyPrint 70.0,
    allowing only `file:` URLs and silencing pyphen's `pkg_resources`
    warning.
  - `new` allocates the next ID after the highest one found in the source
    trees, the export directory, and the git history of both trees.
  - `check-deps` prints a `sudo dnf install …` line for the missing packages
    and never runs sudo.
- Add `tools/hooks/pre-commit`, which runs `orgsyndb validate` and is
  never enabled automatically. Also add `deploy/Caddyfile.example` and
  extend `.gitignore` with the generated and cached directories.
- Add the seed procedures `org/procedures/OSDB-0001-salicylic-acid.org`
  (hydrolysis of methyl salicylate) and `md/procedures/OSDB-0002-aspirin.md`
  (acetylation of salicylic acid, with `precursors = ["OSDB-0001"]`). Both
  are textbook-benign, tagged `sample-data` and marked `status = "draft"`,
  with MW, mmol and equivalents that agree.
- Add tests:
  - pure-logic unit tests;
  - configuration tests that parse `hugo.toml` and `.gitignore`;
  - program tests: usage, `check-deps` under a reduced
    `PATH`, and `clean`;
  - integration tests for export, build, serve, PDF and the hook. These run
    in a temporary copy of the repository whose path contains a space, and
    skip with a stated reason when a tool or a bootstrapped cache is absent.

## Capabilities

### New Capabilities

- `org-export`: how Org sources become Hugo content. Covers the isolated,
  pinned ox-hugo installation, the export plan and its timestamp rules, the
  front-matter mapping and the table-order guard, the body export options,
  and the completeness, freshness and idempotence of `build/export/`.
- `site-build`: the Hugo project and what a build publishes. Covers the
  configuration, the merged procedures section, the minimal layout contract
  that change 3 inherits, the absence of external fetches, Pagefind
  acquisition, and the search index.
- `build-script`: the `tools/orgsyndb` entry point and its helpers.
  Covers the conventions every subcommand follows, the stop on a missing
  tool, each subcommand, `tools/pipeline.py`, the pre-commit hook, the
  Caddyfile example, and the ignore rules.
- `sample-procedures`: the seed procedures. Covers their identity and
  precursor link, sample marking, benign textbook chemistry, quantities
  that agree, and validating with no output lines.

### Modified Capabilities

None. The export conforms to "Org keywords map to exported front matter"
in `procedure-schema` as written: the rule it adds for the autumn fall-back
hour picks one of the two offsets that requirement already accepts. The
validator is invoked exactly as `procedure-validation` defines it. Real
ox-hugo output of the substituted Org template was run through the shipped
validator and passed with no output lines, so the committed fixtures need
no correction.

## Impact

- New files:
  - `tools/export.el`, `tools/pipeline.py`, `tools/orgsyndb` and
    `tools/hooks/pre-commit`;
  - `site/hugo.toml`, `site/content/_index.md` and `site/layouts/*.html`;
  - `deploy/Caddyfile.example`;
  - `org/procedures/OSDB-0001-salicylic-acid.org` and
    `md/procedures/OSDB-0002-aspirin.md`;
  - `tests/test_*.py` files for the new capabilities, and export fixtures
    under `tests/fixtures/export/`.
- Changed files: `.gitignore`. `tools/validate.py` changes only if the
  implementer must expose its Org parsing helpers to `pipeline.py`, and its
  specified behaviour does not change.
- Generated, gitignored paths: `build/`, `public/`, `pdf/`, `.emacs-batch/`,
  `.tools/`, `site/.hugo_build.lock` and `site/resources/`.
- Layout deviation from brief §4: the PDF batch is the `pdf` subcommand.
  `tools/pipeline.py` is added, for the reasons given in design.md D1.
- Dependencies:
  - Fedora packages: `emacs`, `git`, `python3`, `hugo` 0.162.1 and
    `weasyprint` 70.0. `caddy` is optional.
  - Network on first use only: GitHub, for the ox-hugo and tomelr clones and
    the Pagefind release.
- Interfaces fixed for change 3 (`add-site-theme`):
  - The export directory is `build/export/`. The mounts and their `files`
    filter are as above.
  - Layouts live in `site/layouts/`, and change 3 replaces the minimal ones
    while keeping the layout contract in `site-build`.
  - `build` writes the site to `public/` and the Pagefind bundle to
    `public/pagefind/` (`pagefind-ui.js`, `pagefind-ui.css`, `pagefind.js`).
  - `serve` is `http://127.0.0.1:8000/`, and search works there.
  - The seeds take `OSDB-0001` and `OSDB-0002`, so change 3 numbers from
    `OSDB-0003` with `orgsyndb new`.
- Facts the doc writer needs. The final orchestrator task hands these over;
  no relay stage writes these documents.
  - `README.md`:
    - the dependencies and the exact `dnf` line, and the first-run network
      bootstrap (ox-hugo, tomelr and Pagefind, with their pins);
    - `git` is needed for every export, because each export checks the
      pins, while `validate` with explicit arguments needs only Python;
    - `new` cannot see IDs deleted beyond a shallow clone's history, and
      warns;
    - every `orgsyndb` subcommand with its options and outputs: `serve`'s
      URL and `--port`, `pdf`'s output names, and `clean --all`;
    - enabling the hook with `git config core.hooksPath tools/hooks` or a
      symlink, and the fact that it checks the working tree, not the index;
    - the Caddyfile example and the generated directories.
  - `docs/AUTHORING.md` (co-worker, Markdown):
    - `tools/orgsyndb new --md "Title"` and what it fills in;
    - `tools/orgsyndb validate` and how to read its lines;
    - `tools/orgsyndb serve` to preview at `http://127.0.0.1:8000/`;
    - files in `md/procedures/` other than `OSDB-*.md` are never published;
    - a procedure dated in the future is published at once.
  - `docs/AUTHORING-ORG.org` (owner):
    - `tools/orgsyndb new "Title"` and `--ai-model`, and Org timestamps
      in Europe/Berlin under `LC_TIME=C`;
    - the export runs in isolation and never touches `~/.config/emacs`;
    - `$…$` and `\(…\)` are kept as literal text, only braced
      `_{}`/`^{}` become sub- or superscripts, and Babel blocks are never
      evaluated;
    - which offset the export picks for a time in the autumn fall-back
      hour;
    - map-valued front matter is safe in any position, though the template
      keeps `product` last.
