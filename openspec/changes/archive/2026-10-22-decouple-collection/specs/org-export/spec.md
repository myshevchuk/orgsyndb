## MODIFIED Requirements

<!-- Reason: the export's temporary directory belongs with the collection's
other generated files (design.md D3, D10); the remedy in the pin message
names the new program. The fish interpreter no longer runs, so the HOME
check no longer allows for its start-up directories. -->

### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el PLAN_JSON STAGING_DIR`. Before loading package.el or Org it SHALL make these settings:
- `user-emacs-directory`, `package-user-dir` and `package-gnupghome-dir` point to directories inside the application's `.emacs-batch/`.
- `temporary-file-directory` and the `TMPDIR` environment variable point to `tmp/` in the parent directory of `STAGING_DIR`, which is the collection's `build/tmp/`, and which is created when missing.

The export writes nothing under `$HOME`, and nothing in the `TMPDIR` it inherited. It neither loads nor writes anything in `~/.emacs.d` or `~/.config/emacs`. git, which the bootstrap and the pin check run, may still read its own user configuration.

#### Scenario: Owner's directories and the inherited TMPDIR stay untouched
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with `HOME` set to a temporary directory that contains only an empty `.config/emacs/`, and `TMPDIR` set to a separate, empty temporary directory with mode 0555
- **THEN** the export exits 0
- **AND** afterwards that `HOME` contains the empty `.config/emacs/` directory and nothing else, in particular no `.emacs.d`
- **AND** the `TMPDIR` directory is still empty

### Requirement: Pinned ox-hugo and tomelr
`tools/export.el` SHALL install tomelr and then ox-hugo into the application's `.emacs-batch/elpa/` with `package-vc-install`, each at its pinned commit and only when that package is not installed. No package archive is configured. The pins are:
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
