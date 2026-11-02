## ADDED Requirements

### Requirement: Front matter of an Org source
`osdb-org-front-matter` SHALL take the text of an Org source and return the front matter its keywords give, without exporting and without loading Org: an alist of (KEY . VALUE) pairs, KEY a symbol, in the order of their lines and, on one line, of their pairs. `#+TITLE` gives `title` and `#+HUGO_SLUG` gives `slug`, each the keyword's trimmed value; `#+HUGO_TAGS` gives `tags`, the list of its space-separated words; and every `:key value` pair of every `#+HUGO_CUSTOM_FRONT_MATTER` line gives `key` with the Lisp value that `read` returns for the value's text, after one leading `'` is removed. A pair whose value cannot be read is left out. Keyword names match in any case, and lines inside blocks are skipped, as `osdb-org-keywords` skips them.

#### Scenario: Demo source
- **WHEN** an ERT test calls `osdb-org-front-matter` on the text of `examples/demo/org/procedures/OSDB-0007-ethyl-cinnamate.org`
- **THEN** `title` is `"Ethyl cinnamate"`, `slug` is `"osdb-0007"`, `tags` is `("sample-data" "wittig" "cinnamate")`, `id` is `"OSDB-0007"`, `authors` is `("G. Example")`, `working_time` is `5`, `inert_atmosphere` is the symbol `true`, and `products` is `(((compound . "ethyl-cinnamate") (yield_percent . 80)))`
- **AND** the keys come in the order `title`, `slug`, `tags`, `id`, `authors`, `status`, `reaction_types`, `scale`, `notebook`, `project`, `working_time`, `inert_atmosphere`, `substrates`, `hazards`, `references`, `products`

#### Scenario: Blocks and unreadable values
- **WHEN** an ERT test calls `osdb-org-front-matter` on a text holding `#+hugo_custom_front_matter: :status "draft" :scale "5 mmol`, then a `#+begin_example` block holding `#+HUGO_CUSTOM_FRONT_MATTER: :id "OSDB-0001"`
- **THEN** the result is `((status . "draft"))`

## MODIFIED Requirements

### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el ORG_ROOT STAGING_DIR`, and SHALL work with Emacs 29.1 or later and the Org it bundles. `ORG_ROOT` is the directory of Org sources, and `tools/orgsyndb` passes `org/procedures` with the collection as working directory. It loads neither package.el nor any package archive. Before loading Org or `emacs/osdb-org.el` it SHALL make these settings:
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

On every run that goes on to export, that is, every run whose Org sources have no error and include at least one Org source, the export compares each installed checkout's `HEAD` with its pin. On a mismatch it exits non-zero, before exporting anything, with a message that names the package, both commits, and `tools/orgsyndb clean --all`.

#### Scenario: Installed checkouts are at the pins
- **WHEN** an integration test reads `git rev-parse HEAD` in `.emacs-batch/elpa/ox-hugo` and `.emacs-batch/elpa/tomelr` after an export
- **THEN** the values are `b7dc44dc28911b9d8e3055a18deac16c3b560b03` and `670e0a08f625175fd80137cf69e799619bf8a381`

#### Scenario: A checkout at another commit stops the export
- **WHEN** an integration test copies `.emacs-batch/` into the application copy instead of linking it, checks out ox-hugo's parent commit in the copy, and runs `tools/orgsyndb -C <collection> export`
- **THEN** the exit status is non-zero, and the output contains `ox-hugo`, `b7dc44dc28911b9d8e3055a18deac16c3b560b03`, the parent commit's hash, and `clean --all`
- **AND** `build/export/` is unchanged

#### Scenario: No package.el
- **WHEN** a test reads `tools/export.el` and `emacs/osdb-org.el`
- **THEN** neither contains `package-vc` or `(require 'package)`

### Requirement: Org front-end library
`emacs/osdb-org.el` SHALL hold every function of the export that reads Org text or Org file names, together with the timestamp arithmetic, and loading it SHALL have no effect beyond defining its functions and constants. It loads neither Org nor ox-hugo nor tomelr. It reads no command-line argument, starts no export and never calls `kill-emacs`. It provides the feature `osdb-org`, and `tools/export.el` loads it from the application's `emacs/` directory after making the settings of "Isolated batch Emacs". It defines at least the functions that the ERT scenarios of this capability, procedure-schema and localization call: `osdb-org-examine`, `osdb-org-problem-line`, `osdb-org-check-file-name`, `osdb-org-local-instants`, `osdb-org-export-instants`, `osdb-org-rfc3339` and `osdb-org-zone-available-p`, and the function `osdb-org-front-matter` that the editor calls ("Front matter of an Org source").

`osdb-org-examine` takes a directory and returns a pair of the sources and the problems, as follows:
- The sources are the Org sources without any problem, in name order. Each carries its absolute path, its stem (the file name without `.org`), its `date` and `lastmod` as `YYYY-MM-DDThh:mm:ss+HH:MM` strings, and its AI model, or none when `#+AI_MODEL` is absent or `none`.
- The problems are path and problem pairs, in report order. Each problem has a field, a severity and a message.

#### Scenario: Library loads alone
- **WHEN** an ERT test, running in the suite's `emacs -Q --batch` after it loaded `emacs/osdb-org.el`, checks which features are present
- **THEN** `osdb-org` is a feature, and `org`, `ox-hugo` and `tomelr` are not

### Requirement: ERT suite
The repository SHALL ship an ERT suite, `tests/el/osdb-org-tests.el`, that proves every scenario stated as an ERT test in this capability, procedure-schema and localization. Each test names its scenario in its docstring. The suite has these properties:
- It runs with `emacs -Q --batch -l <repo>/tests/el/osdb-org-tests.el -f ert-run-tests-batch-and-exit` from any working directory.
- It loads `emacs/osdb-org.el` relative to its own location.
- It needs neither ox-hugo nor tomelr nor network access.
- It reads its fixtures from `tests/fixtures/`.

In ERT scenarios, an Org fixture path such as `org-invalid/missing-created/org/OSDB-0201-missing-created.org` is relative to `tests/fixtures/`. "Examines F" means calling `osdb-org-examine` on the directory holding F. "Reports exactly one error with field F containing T" means that the call returns exactly one problem, and that problem has field F, severity `error` and a message containing T. "The problem lines are exactly L" means that formatting every returned problem with `osdb-org-problem-line` gives the lines L and no others, in that order, where `R` stands for the directory as it was given to `osdb-org-examine`. These comparisons are of whole lines.

`tests/test_elisp.py` runs that command under pytest. It passes when the command exits 0, shows the command's output when it does not, and skips with a reason that names `emacs` when `emacs` is absent, so that `python3 -m pytest tests` stays the single entry point.

#### Scenario: ERT suite under pytest
- **WHEN** `python3 -m pytest tests/test_elisp.py` runs with `emacs` on `PATH`
- **THEN** it passes, having run the ERT suite with no failed or skipped ERT test

#### Scenario: ERT suite without Emacs
- **WHEN** `python3 -m pytest -rs tests/test_elisp.py` runs with a `PATH` that holds `python3` but no `emacs`
- **THEN** its test is skipped with a reason that names `emacs`
