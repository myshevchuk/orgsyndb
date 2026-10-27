## MODIFIED Requirements

### Requirement: Export checked on Emacs 29
The repository SHALL ship `.github/workflows/emacs-29.yml`, a GitHub Actions workflow that checks the export and the ERT suite on the oldest supported Emacs:
- **Triggers.** It runs on a push to `main`, on pull requests and on manual dispatch (`workflow_dispatch`).
- **Permissions.** Its permissions are `contents: read`.
- **Job.** A job named `export` runs on `ubuntu-24.04`. It installs `emacs-nox` and `git` with `apt-get install --no-install-recommends`, sets up Python 3.14 with `actions/setup-python`, and installs pytest with pip. It runs `tools/orgsyndb -C examples/demo export`, and then `python -m pytest tests/test_export_integration.py tests/test_elisp.py`.

#### Scenario: Workflow is wired
- **WHEN** a test reads `.github/workflows/emacs-29.yml` as text
- **THEN** its triggers name `push` with branch `main`, `pull_request` and `workflow_dispatch`, and its permissions are `contents: read`
- **AND** the `export` job runs on `ubuntu-24.04`, names an `apt-get install` with `--no-install-recommends` of `emacs-nox` and `git`, `actions/setup-python` with Python `3.14`, and the commands `tools/orgsyndb -C examples/demo export` and `python -m pytest tests/test_export_integration.py tests/test_elisp.py`, in that order
