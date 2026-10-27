## MODIFIED Requirements

### Requirement: Pipeline helper module
`tools/pipeline.py` SHALL be a Python 3.14 module that uses only the standard library, besides importing `validate` from its own directory, and it annotates every callable. It has no command-line interface: `tools/orgsyndb` imports it, and the messages it prints name the program `orgsyndb`. It reads no Org source; of `org/procedures/` it reads only the entry names. The only Org files it reads are the documents of the application's `docs/` that it stages as help pages (site-help spec). It exposes the functions `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `fill_template`, `has_org_sources`, `org_stems`, `org_error_reported`, `check_staging`, `recover_export`, `replace_export`, `new_procedure`, `pdf_jobs`, `install_pagefind`, `ensure_pagefind`, `hugo_overlay`, `help_slug`, `help_page`, `stage_help` and `remove_tree`.

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/pipeline.py` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `validate`

#### Scenario: No command-line interface
- **WHEN** a test reads `tools/pipeline.py`
- **THEN** it is not executable, does not begin with `#!`, and has no `if __name__ == "__main__":` block

#### Scenario: No Org reading in Python
- **WHEN** a test reads `tools/pipeline.py`, `tools/validate.py` and `tools/orgsyndb`
- **THEN** none contains `--org-root`, `export-plan`, `lint_org`, `cross_check` or `export_instants`
