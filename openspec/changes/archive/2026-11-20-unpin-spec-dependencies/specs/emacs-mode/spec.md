## MODIFIED Requirements

### Requirement: Package files
The application SHALL ship the Emacs package `orgsyndb` in its `emacs/` directory. `emacs/orgsyndb.el` provides the feature `orgsyndb` and carries the headers of a package named `orgsyndb`, with a `Package-Requires` header naming the oldest Emacs it supports. The package's other files are `emacs/orgsyndb-<part>.el` and the Org front end `emacs/osdb-org.el` (org-export "Org front-end library"). The package uses only libraries that this oldest Emacs ships; only `emacs/orgsyndb-flycheck.el` refers to Flycheck, and it does not require it. Loading `orgsyndb` defines functions, modes, variables and options and changes no other state: it turns on no mode and adds to no global hook or list. `global-orgsyndb-mode` and the commands are autoloaded.

#### Scenario: Clean byte compilation
- **WHEN** a test byte-compiles each file under `emacs/` in its own `emacs -Q --batch` with `byte-compile-error-on-warn` set and only `emacs/` added to `load-path`
- **THEN** every compilation succeeds

#### Scenario: Loading changes nothing
- **WHEN** an ERT test records the global values of `before-save-hook`, `after-save-hook`, `completion-at-point-functions`, `xref-backend-functions`, `flymake-diagnostic-functions` and `eldoc-documentation-functions` and the value of `time-stamp-format`, then loads `orgsyndb`
- **THEN** each value is unchanged, `global-orgsyndb-mode` is off, and `org` is not a feature
