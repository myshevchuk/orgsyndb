## Why

A procedure's `authors` are free-text names, matched by nobody: the
same person can appear as `A. Example` and `A Example`, the lab
application cannot tell who wrote what, and draft 07's import keeps
authors as accounts. The owner settled that procedure authors are lab
accounts, named in the files by user name, and that user names are
limited to what Forgejo takes and fixed once set, so both programs
show the same name.

## What Changes

- **BREAKING** A procedure's `authors` are user names of the registry's
  accounts; the validator refuses an unknown or repeated one.
- User names are at most 40 letters and digits with single `.`, `-` or
  `_` between them, and cannot change once an account exists.
- The snapshot lists every account's user name and name, inside its
  digest, so renaming a person rebuilds the site.
- The build stages the authors' names; the site's author terms are
  user names (`/authors/<user name>/`), and every place that writes an
  author writes the account's name.
- The manifest carries each procedure's authors; the import keeps them
  as rows and refuses an unknown user name.
- The index lists the accounts; Emacs completes authors from them.
- The demo's procedures credit its five accounts; the test collections
  name fictitious accounts `<initial>.example`.

## Capabilities

### New Capabilities

- `procedure-authors`: authors as accounts, and the author data the
  site shows.

### Modified Capabilities

- `procedure-schema`: the `authors` field.
- `lab-registry`: accounts in the snapshot; `registry_load` ignores
  them.
- `web-app`: the user-name rule.
- `site-catalogue`, `site-theme`, `site-search`: author keys, URLs and
  names.
- `sample-procedures`: the samples' authors.
- `emacs-mode`, `collection-index`: authors from the accounts.
- `build-script`: the author data and the manifest's authors.
- `collection-import`: procedure authors, their check and their rows.
- `org-export`: the demo's exported authors.

## Impact

- Changed: `webapp/accounts/` (user-name validation, admin),
  `webapp/registry/snapshot.py`, `webapp/collection/` (model,
  migration, import), `webapp/demo/` (registry file and manifest),
  `tools/validate.py`, `tools/pipeline.py`, the site layouts that write
  authors, `emacs/`, `examples/demo/`, `tests/fixtures/` and the
  registries the tests use, the tests of each.
- Docs: `README.md`, `docs/SCHEMA*.md`, `docs/AUTHORING*.md` and
  `docs/AUTHORING-ORG*.org` where they describe authors;
  `webapp/docs/database-schema.html`, regenerated.
