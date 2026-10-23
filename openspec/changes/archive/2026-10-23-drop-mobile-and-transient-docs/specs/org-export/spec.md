## MODIFIED Requirements

### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el PLAN_JSON STAGING_DIR`, and SHALL work with Emacs 30.2 and the Org 9.7.11 it bundles. Before loading package.el or Org it SHALL make these settings:
- `user-emacs-directory`, `package-user-dir` and `package-gnupghome-dir` point to directories inside the application's `.emacs-batch/`.
- `temporary-file-directory` and the `TMPDIR` environment variable point to `tmp/` in the parent directory of `STAGING_DIR`, which is the collection's `build/tmp/`, and which is created when missing.

The export writes nothing under `$HOME`, and nothing in the `TMPDIR` it inherited. It neither loads nor writes anything in `~/.emacs.d` or `~/.config/emacs`. git, which the bootstrap and the pin check run, may still read its own user configuration.

#### Scenario: Owner's directories and the inherited TMPDIR stay untouched
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with `HOME` set to a temporary directory that contains only an empty `.config/emacs/`, and `TMPDIR` set to a separate, empty temporary directory with mode 0555
- **THEN** the export exits 0
- **AND** afterwards that `HOME` contains the empty `.config/emacs/` directory and nothing else, in particular no `.emacs.d`
- **AND** the `TMPDIR` directory is still empty

