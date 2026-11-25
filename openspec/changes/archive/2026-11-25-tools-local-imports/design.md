## Context

`tools/` runs directly under system `python3` without a virtual
environment in author checkouts, `tools/hooks/pre-commit`, Emacs
flycheck, GitHub Actions, and `deploy/docker/Dockerfile`. The
no-third-party-dependency guarantee remains essential, whereas blocking
internal modules under `tools/` is accidental friction because `tools/`
is always shipped as a directory.

## Goals / Non-Goals

- **Goals:** Preserve the zero-third-party-package invariant across
  `tools/`; permit local sibling modules and packages under `tools/`;
  stop pinning an internal function inventory in `build-script`.
- **Non-Goals:** Splitting `tools/validate.py` or `tools/pipeline.py`
  now, or introducing third-party dependencies in `tools/`.

## Decisions

- Define local modules in tests as top-level `*.py` file stems and
  subdirectories with `__init__.py` directly under `tools/`.
- Check absolute imports (`node.level == 0`) of `tools/validate.py`,
  `tools/pipeline.py`, `tools/orgsyndb`, and every `.py` file under
  `tools/` against `sys.stdlib_module_names | local_tool_modules()` so
  no local helper can introduce a third-party dependency either.
