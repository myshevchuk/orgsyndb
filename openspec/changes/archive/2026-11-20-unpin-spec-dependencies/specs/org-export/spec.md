## MODIFIED Requirements

### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el ORG_ROOT STAGING_DIR`, and SHALL work with the oldest Emacs the package `orgsyndb` supports (emacs-mode "Package files") or a later one, and the Org it bundles. `ORG_ROOT` is the directory of Org sources, and `tools/orgsyndb` passes `org/procedures` with the collection as working directory. It loads neither package.el nor any package archive. Before loading Org or `emacs/osdb-org.el` it SHALL make these settings:
- `user-emacs-directory` points to the application's `.emacs-batch/`.
- `temporary-file-directory` and the `TMPDIR` environment variable point to `tmp/` in the parent directory of `STAGING_DIR`, which is the collection's `build/tmp/`, and which is created when missing.

Under an older Emacs it exits 1 before installing or exporting anything, printing `export.el: error: Emacs <oldest> or later is required; this is Emacs <version>`.

The export writes nothing under `$HOME`, and nothing in the `TMPDIR` it inherited. It neither loads nor writes anything in `~/.emacs.d` or `~/.config/emacs`. git, which the bootstrap and the pin check run, may still read its own user configuration.

#### Scenario: Owner's directories and the inherited TMPDIR stay untouched
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with `HOME` set to a temporary directory that contains only an empty `.config/emacs/`, and `TMPDIR` set to a separate, empty temporary directory with mode 0555
- **THEN** the export exits 0
- **AND** afterwards that `HOME` contains the empty `.config/emacs/` directory and nothing else, in particular no `.emacs.d`
- **AND** the `TMPDIR` directory is still empty

#### Scenario: An old Emacs is refused
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with an `emacs` on `PATH` that runs the real Emacs with `emacs-version` set to a version older than the oldest supported one before `tools/export.el` loads
- **THEN** the export exits 1, the output contains `Emacs <oldest> or later is required; this is Emacs <that version>`, and `build/export/` is unchanged

### Requirement: Pinned ox-hugo and tomelr
`tools/export.el` SHALL install tomelr and then ox-hugo, each only when its directory `.emacs-batch/elpa/<package>/` in the application does not exist, by cloning the package's upstream repository with git into that directory and checking out its pinned commit. When the clone or the checkout fails, it removes the directory and exits non-zero with a message naming the package. It then adds both directories to `load-path`. The upstream repositories are `https://github.com/kaushalmodi/tomelr` and `https://github.com/kaushalmodi/ox-hugo`; `tools/export.el` names the pinned commit of each.

On every run that goes on to export, that is, every run whose Org sources have no error and include at least one Org source, the export compares each installed checkout's `HEAD` with its pin. On a mismatch it exits non-zero, before exporting anything, with a message that names the package, both commits, and `tools/orgsyndb clean --all`.

#### Scenario: Installed checkouts are at the pins
- **WHEN** an integration test reads `git rev-parse HEAD` in `.emacs-batch/elpa/ox-hugo` and `.emacs-batch/elpa/tomelr` after an export
- **THEN** the values are the commits `tools/export.el` pins for them

#### Scenario: A checkout at another commit stops the export
- **WHEN** an integration test copies `.emacs-batch/` into the application copy instead of linking it, checks out ox-hugo's parent commit in the copy, and runs `tools/orgsyndb -C <collection> export`
- **THEN** the exit status is non-zero, and the output contains `ox-hugo`, its pinned commit, the parent commit's hash, and `clean --all`
- **AND** `build/export/` is unchanged

#### Scenario: No package.el
- **WHEN** a test reads `tools/export.el` and `emacs/osdb-org.el`
- **THEN** neither contains `package-vc` or `(require 'package)`
