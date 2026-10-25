## MODIFIED Requirements

### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el PLAN_JSON STAGING_DIR`, and SHALL work with Emacs 29.1 or later and the Org it bundles. It loads neither package.el nor any package archive. Before loading Org it SHALL make these settings:
- `user-emacs-directory` points to the application's `.emacs-batch/`.
- `temporary-file-directory` and the `TMPDIR` environment variable point to `tmp/` in the parent directory of `STAGING_DIR`, which is the collection's `build/tmp/`, and which is created when missing.

Under an Emacs older than 29.1 it exits 1 before installing or exporting anything, printing `export.el: error: Emacs 29.1 or later is required; this is Emacs <version>`.

The export writes nothing under `$HOME`, and nothing in the `TMPDIR` it inherited. It neither loads nor writes anything in `~/.emacs.d` or `~/.config/emacs`. git, which the bootstrap and the pin check run, may still read its own user configuration.

#### Scenario: Owner's directories and the inherited TMPDIR stay untouched
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with `HOME` set to a temporary directory that contains only an empty `.config/emacs/`, and `TMPDIR` set to a separate, empty temporary directory with mode 0555
- **THEN** the export exits 0
- **AND** afterwards that `HOME` contains the empty `.config/emacs/` directory and nothing else, in particular no `.emacs.d`
- **AND** the `TMPDIR` directory is still empty

#### Scenario: An old Emacs is refused
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with an `emacs` on `PATH` that runs the real Emacs with `emacs-version` set to `28.2` before `tools/export.el` loads
- **THEN** the export exits 1, the output contains `Emacs 29.1 or later is required; this is Emacs 28.2`, and `build/export/` is unchanged

### Requirement: Pinned ox-hugo and tomelr
`tools/export.el` SHALL install tomelr and then ox-hugo, each only when its directory `.emacs-batch/elpa/<package>/` in the application does not exist, by cloning the package's upstream repository with git into that directory and checking out its pinned commit. When the clone or the checkout fails, it removes the directory and exits non-zero with a message naming the package. It then adds both directories to `load-path`. The pins are:
- tomelr: `https://github.com/kaushalmodi/tomelr` at `670e0a08f625175fd80137cf69e799619bf8a381` (0.4.3).
- ox-hugo: `https://github.com/kaushalmodi/ox-hugo` at `b7dc44dc28911b9d8e3055a18deac16c3b560b03` (MELPA `20251206.1738`).

On every run, the export compares each installed checkout's `HEAD` with its pin. On a mismatch it exits non-zero, before exporting anything, with a message that names the package, both commits, and `tools/orgsyndb clean --all`.

#### Scenario: Installed checkouts are at the pins
- **WHEN** an integration test reads `git rev-parse HEAD` in `.emacs-batch/elpa/ox-hugo` and `.emacs-batch/elpa/tomelr` after an export
- **THEN** the values are `b7dc44dc28911b9d8e3055a18deac16c3b560b03` and `670e0a08f625175fd80137cf69e799619bf8a381`

#### Scenario: A checkout at another commit stops the export
- **WHEN** an integration test copies `.emacs-batch/` into the application copy instead of linking it, checks out ox-hugo's parent commit in the copy, and runs `tools/orgsyndb -C <collection> export`
- **THEN** the exit status is non-zero, and the output contains `ox-hugo`, `b7dc44dc28911b9d8e3055a18deac16c3b560b03`, the parent commit's hash, and `clean --all`
- **AND** `build/export/` is unchanged

#### Scenario: No package.el
- **WHEN** a test reads `tools/export.el`
- **THEN** it contains neither `package-vc` nor `(require 'package)`

## ADDED Requirements

### Requirement: Export checked on Emacs 29
The repository SHALL ship `.github/workflows/emacs-29.yml`, a GitHub Actions workflow that checks the export on the oldest supported Emacs:
- **Triggers.** It runs on a push to `main`, on pull requests and on manual dispatch (`workflow_dispatch`).
- **Permissions.** Its permissions are `contents: read`.
- **Job.** A job named `export` runs on `ubuntu-24.04`. It installs `emacs-nox` and `git` with `apt-get`, sets up Python 3.14 with `actions/setup-python`, installs pytest with pip, runs `tools/orgsyndb -C examples/demo export`, and then runs `python -m pytest tests/test_export_integration.py`.

#### Scenario: Workflow is wired
- **WHEN** a test reads `.github/workflows/emacs-29.yml` as text
- **THEN** its triggers name `push` with branch `main`, `pull_request` and `workflow_dispatch`, and its permissions are `contents: read`
- **AND** the `export` job runs on `ubuntu-24.04`, names an `apt-get install` of `emacs-nox` and `git`, `actions/setup-python` with Python `3.14`, and the commands `tools/orgsyndb -C examples/demo export` and `python -m pytest tests/test_export_integration.py`, in that order
