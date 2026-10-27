## Why

The README calls OrgSynDB "designed for Fedora", and `orgsyndb` prints
`sudo dnf install ...` for a missing tool. Nothing in the application
depends on Fedora: Python, Hugo, WeasyPrint, Emacs and Git are packaged
by every major Linux distribution and by other Unix-like systems.
Fedora is only the author's distribution.

## What Changes

- The missing-tool error and the `check-deps` summary line name the
  missing tools and point to the system's package manager instead of
  printing a `dnf` command.
- The README's installation section stops naming Fedora as the target
  and shows the install commands for Fedora (`dnf`) and Debian/Ubuntu
  (`apt`), with the tool versions the project is tested with.
- The demo-site workflow keeps its `fedora:44` container: it is a CI
  choice, not a platform requirement, and the Emacs 29 workflow already
  runs on Ubuntu.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-script`: missing-tool message and `check-deps` summary line.

## Impact

- `tools/orgsyndb`, `tests/test_build_script.py`.
- Docs: `README.md`.
