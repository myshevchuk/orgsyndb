## 1. Demo collection

- [x] 1.1 `git mv` `org/` to `examples/demo/org/`, `md/` to
      `examples/demo/md/` and `site/static/structures/` to
      `examples/demo/static/structures/` (design.md D7).
- [x] 1.2 Add `examples/demo/orgsyndb.toml` (`format = 1`) and
      `examples/demo/.gitignore`, identical to what `init` writes.

## 2. Program and helpers

- [x] 2.1 Add `tools/orgsyndb` (D5): global `-C`/`--collection`, collection
      discovery and marker checks (D1, D2), every subcommand of
      `build.fish`, and `init` (D8).
- [x] 2.2 `pipeline.py`: `PROG`, `hugo_overlay` (D4), `new`/`next-id` with
      `--collection` and templates from the application, next-ID history
      for a collection inside any work tree (D7).
- [x] 2.3 `site/hugo.toml`: drop `publishDir` and `module.mounts` (D4).
- [x] 2.4 `export.el`: temporary directory beside the staging directory,
      pin remedy names `tools/orgsyndb clean --all` (D10).
- [x] 2.5 `validate.py`: default `--static-dir` is `static` (D9).
- [x] 2.6 `tools/hooks/pre-commit` in POSIX `sh` (D6); remove
      `tools/build.fish`.
- [x] 2.7 `templates/procedure.md`: the structure-image comment names the
      collection's `static/structures/`.

## 3. Tests

- [x] 3.1 Harness (D12): `Sandbox.app` and `Sandbox.root`, the program run
      with `-C`, `require_exporter` without fish.
- [x] 3.2 Replace the fish tests with program tests: usage, help, symlink,
      syntax, imports, no fish, missing tools, validate pass-through,
      clean, check-deps, port range.
- [x] 3.3 Add the `collection` tests: marker errors, discovery from a
      subdirectory, no collection, `-C` without marker, untouched `site/`,
      `init`, demo equals `init`.
- [x] 3.4 Update the pipeline tests for `--collection`, and add the
      subdirectory-history scenario; add the overlay scenario.
- [x] 3.5 Point sample, theme and export tests at `examples/demo/`; tighten
      the `HOME` check; add the hook-through-symlink scenario and the
      default-static-directory scenario.
- [x] 3.6 Full suite green with every optional tool present except Caddy.

## 4. Documents

- [x] 4.1 README: application and collections, the demo, `init`, the
      command reference, migration from `build.fish`.
- [x] 4.2 Authoring guides and schema reference: commands and the
      structure-image location.
- [x] 4.3 `deploy/Caddyfile.example`: the collection's `public/`.

## 5. Review

- [x] 5.1 Review by a separate session after implementation; its fixes
      are in `fix(orgsyndb): find collection before tool checks`. No
      design check ran before implementation: the owner asked for the
      change directly.
- [ ] 5.2 Owner verifies on Fedora 44 with Emacs 30: `check-deps`, a demo
      build, `init` and a first private procedure. Left open at archive:
      the owner does it after the merge.

## 6. Archive

- [x] 6.1 Apply the deltas to `openspec/specs/`, add the `collection`
      capability, and rewrite every remaining `tools/build.fish` mention
      and repository-relative content path in the main specs as design.md
      D11 describes.
