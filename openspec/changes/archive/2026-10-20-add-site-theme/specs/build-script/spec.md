## MODIFIED Requirements

<!-- Reason: the behaviour is unchanged. The scenario "One PDF per
procedure, no stale files" expected exactly the two seed PDFs;
add-site-theme ships six more procedures, so it now expects exactly one
PDF per procedure content file. -->

### Requirement: pdf subcommand
`tools/build.fish pdf` SHALL run `build`, delete `pdf/`, and run `tools/pipeline.py pdf --public <repo>/public --pdf-dir <repo>/pdf build/export md/procedures`. That command does the following:
- It renders one PDF per procedure content file. The output is `pdf/<content file stem>.pdf`, rendered from `public/procedures/<slug>/index.html`.
- It invokes `weasyprint --allowed-protocols file <html> <pdf>` with `PYTHONWARNINGS` set so that pyphen's `pkg_resources is deprecated` `UserWarning` is not shown.
- A job fails when WeasyPrint exits non-zero or writes a line beginning `ERROR:`. A failed job's output file is removed, and the remaining jobs still run.
- It prints one line per PDF, and exits 1 when any job failed.

`pipeline.pdf_jobs(files, public, pdf_dir)` computes the jobs from `(content path, front matter)` pairs, sorted by PDF name. When an HTML input is missing, it raises `ValueError` naming that path.

#### Scenario: Job naming
- **WHEN** a test calls `pdf_jobs` with `md/procedures/OSDB-0002-aspirin.md` and front matter `slug = "osdb-0002"`, with `public` and `pdf` as given directories
- **THEN** the single job's input is `<public>/procedures/osdb-0002/index.html` and its output is `<pdf>/OSDB-0002-aspirin.pdf`

#### Scenario: Missing page
- **WHEN** a test calls `pdf_jobs` with a content file whose page does not exist under `public`
- **THEN** it raises `ValueError`, whose message contains the expected HTML path

#### Scenario: One PDF per procedure, no stale files
- **WHEN** an integration test places `pdf/OSDB-0999-stale.pdf` in the temporary repository and runs `tools/build.fish pdf`
- **THEN** it exits 0, `pdf/` holds exactly one file `<stem>.pdf` for each procedure content file `<stem>.md` in `build/export/` and `md/procedures/`, among them `OSDB-0001-salicylic-acid.pdf` and `OSDB-0002-aspirin.pdf`, and each file begins with `%PDF-`
- **AND** neither stdout nor stderr contains `pkg_resources`

#### Scenario: Remote stylesheet fails the job
- **WHEN** an integration test adds `<link rel="stylesheet" href="https://cdn.example.invalid/x.css">` to the temporary repository's procedure layout and runs `tools/build.fish pdf`
- **THEN** it exits 1, and stderr names the failing PDF
