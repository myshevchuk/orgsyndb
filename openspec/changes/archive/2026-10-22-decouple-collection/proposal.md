## Why

The repository mixes two things with different owners and audiences: the
OrgSynDB application (pipeline, theme, schema, tests) and the procedures it
publishes. The owner wants to develop the application in the open while the
real procedures, which are in effect company data, stay in a private
repository. Today the build reads `org/procedures/`, `md/procedures/` and
`site/static/structures/` from its own checkout, so the two cannot be
separated.

The build entry point is also a fish script. fish is an interactive user
shell; it is not installed on an ordinary server, and requiring it there is
an unusual dependency for a build tool. Python 3 is already a hard
dependency, and every piece of logic the fish script calls lives in Python
already.

## What Changes

- **Collections.** Procedures live in a *collection*: any directory with an
  `orgsyndb.toml` marker (`format = 1`), holding `org/procedures/`,
  `md/procedures/` and an optional `static/` (structure images). Every
  generated file of a build (`build/`, `public/`, `pdf/`, Hugo's resource
  cache) is written inside the collection. The application directory is
  written only by its two fetched-tool caches, `.emacs-batch/` and `.tools/`.
- **Demo collection.** The eight sample procedures and the structure image
  move to `examples/demo/`, a complete collection shipped with the
  application and used by the tests.
- **`tools/orgsyndb` replaces `tools/build.fish`.** A stdlib-only Python 3.14
  program with the same subcommands, steps, messages and exit statuses,
  plus:
  - a global `-C DIR` / `--collection DIR` option; without it the collection
    is the nearest directory, from the working directory upwards, that
    holds `orgsyndb.toml`;
  - `init DIR`, which creates an empty collection.

  It calls `tools/pipeline.py` and `tools/validate.py` in-process instead of
  as subprocesses. fish is no longer used anywhere.
- **Hugo configuration split.** `site/hugo.toml` keeps the site-wide
  settings. The build writes an overlay into
  `<collection>/build/hugo-config/`, holding `publishDir`, `resourceDir` and
  the module mounts as absolute paths, and passes it to Hugo with
  `--configDir` and `--noBuildLock`.
- `tools/hooks/pre-commit` becomes a POSIX `sh` script meant for a
  collection's repository: it validates the collection at the top of the
  work tree with the application it belongs to.
- `pipeline.py new` takes `--collection` instead of `--repo` and reads the
  templates from the application. Next-ID history works for a collection in
  any git work tree, including a subdirectory such as `examples/demo/`.
- `export.el` puts its temporary directory in `<build>/tmp/`, beside the
  staging directory it is given, instead of in the application.
- The validator's default `--static-dir` becomes `static` in the working
  directory, since structure images now belong to a collection.

**BREAKING:** `tools/build.fish` is replaced by
`tools/orgsyndb -C <collection> …`.

## Capabilities

### New Capabilities

- `collection`: what a collection is, how the program finds it, what it
  writes into it, and `init`.

### Modified Capabilities

- `build-script`: the entry point, its conventions, the subcommands' paths,
  `new`, `clean`, the pre-commit hook and the ignore rules.
- `site-build`: the Hugo configuration and its generated overlay.
- `org-export`: the temporary directory and the pin-mismatch remedy.
- `procedure-validation`: the default static directory.
- `sample-procedures`: the samples form the demo collection.

## Impact

- Code: `tools/orgsyndb` (new), `tools/build.fish` (removed),
  `tools/pipeline.py`, `tools/export.el`, `tools/validate.py`,
  `tools/hooks/pre-commit`, `site/hugo.toml`, `templates/procedure.md`.
- Data: `org/`, `md/` and `site/static/structures/` move to
  `examples/demo/`.
- Tests: the sandbox becomes an application copy plus a collection copy;
  the fish-specific tests become Python and `sh` tests.
- Docs: README, both authoring guides and the schema reference.
- Dependencies: fish is dropped. Nothing is added.
