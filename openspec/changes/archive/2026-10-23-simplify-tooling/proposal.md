## Why

The build program grew quickly from a fish script that called
`tools/pipeline.py` as a subprocess. `tools/orgsyndb` now imports the
pipeline and calls it directly, but the pipeline's own command line,
the program's argument pass-through to the validator, and the ignore
rules for the old in-application build output remain. They duplicate
`orgsyndb`, keep extra error paths alive, and are documented and tested
as if someone used them. A few smaller duplications came with them.

## What Changes

- **BREAKING** Remove the command line of `tools/pipeline.py`
  (`export-plan`, `recover-export`, `install-export`, `next-id`, `new`,
  `pdf`, `ensure-pagefind`); it becomes a plain module. The tests call
  its functions directly. Its messages always name `orgsyndb`.
- Check the title and the `--ai-model` and `--lang` values of `new` in
  one place, `pipeline.new_procedure`, instead of three.
- **BREAKING** Remove `orgsyndb validate ARGS...`; any argument to
  `validate` is a usage error. `tools/validate.py` stays the way to
  validate arbitrary directories.
- Stop ignoring `build/`, `public/`, `pdf/`, `site/.hugo_build.lock`
  and `site/resources/` in the application; no build writes them.
- Drop the "(tested with X)" notes from `check-deps`.
- Smaller clean-ups: one argument check in `export.el` instead of two,
  one tree-removal helper shared by `orgsyndb` and the pipeline, and a
  validate step line that names the directories rather than a
  `validate.py` command line nobody typed.

## Impact

Affects the build-script, collection, org-export, site-build and
localization capabilities, `tools/orgsyndb`, `tools/pipeline.py`,
`tools/export.el`, `.gitignore`, the pipeline, export-plan,
localization and build-script tests, and the README. A stale
`site/.hugo_build.lock` or `site/resources/` in an old checkout now
shows up as untracked and can be deleted.
