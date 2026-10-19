## 1. Test fixtures and harness (test writer)

House rules for the tests:

- Tests are `unittest.TestCase` classes in `tests/test_*.py`, named for
  behaviour and run with `python3 -m pytest tests`.
- Tests locate the repository from their own `__file__`.
- Paths are passed as list arguments, never through a shell string.
- Names are fictitious, and no user or machine identifier appears.

Definitions of "integration test" and "fish test" are in the spec
comments, and the test layers are in design.md D18.

- [x] 1.1 Add `tests/fixtures/export/OSDB-0901-table-first.org`, a fully
      valid Org procedure with all eight sections:
      - its first `#+HUGO_CUSTOM_FRONT_MATTER:` line sets `:product`, and
        later lines set `:id`, `:authors`, `:status`, `:reaction_types`,
        `:scale`, `:yield_percent`, `:hazards` and
        `:precursors '("OSDB-0001")`;
      - `#+AI_MODEL: example-model-1`;
      - `#+CREATED: [2026-10-19 Mon 17:42:05]` and
        `#+LAST_MODIFIED: [2026-10-19 Mon 21:00:07]`.
- [x] 1.2 Add `tests/fixtures/export/OSDB-0902-literal-text.org`, a fully
      valid Org procedure with `#+AI_MODEL: none`. Its Summary contains
      `Costs $5 and $10, $x$ and \(y^2\).` and
      `H_{2}O, CO_2 and yield_percent`. It also has an `emacs-lisp` source
      block with `:exports results` that would create the file named by the
      environment variable `OSDB_TEST_MARKER`.
- [x] 1.3 Add `tests/fixtures/export/OSDB-0903-named-paragraph.org`, a
      fully valid Org procedure with `#+AI_MODEL: none`. Its Summary holds a
      paragraph preceded by `#+name: observation` and its Notes another
      preceded by `#+name: second`. This is the regression fixture for
      random reference IDs: without the seed in design.md D6, two exports
      of it differ. IDs 0901 to 0903 keep committed fixture IDs unique.
- [x] 1.4 Add an integration harness module (e.g.
      `tests/pipeline_support.py`). It does the following:
      - builds a temporary repository copy whose path contains a space,
        copying `tools/`, `site/`, `templates/`, `org/`, `md/` and
        `tests/fixtures/export/`;
      - symlinks `.emacs-batch/` and `.tools/` from the real repository,
        with an option to copy `.emacs-batch/` instead;
      - runs `tools/build.fish` with `cwd` set to a second temporary
        directory;
      - builds a reduced `PATH` from named tools plus a recording fake
        `sudo`;
      - makes a read-only (mode 0555) temporary `TMPDIR`, and restores
        its mode for clean-up;
      - finds a free TCP port;
      - provides skip helpers that name the missing tool or cache. For an
        unbootstrapped `.emacs-batch/` the reason is "ox-hugo not
        bootstrapped: run tools/build.fish export once (needs network)".

## 2. Failing tests (test writer)

Write each test so that, once the module or script it exercises exists, it
fails on its assertion and not on an import or setup error. The function
names and signatures to test against are in design.md D1.

- [x] 2.1 `tests/test_pipeline_logic.py` covers these scenarios:
      - from `build-script` "new subcommand": next ID, first ID, exhausted
        ID space, the deleted committed procedure (skip without `git`),
        the shallow clone (skip without `git`), slugs, long and empty
        titles, Org timestamps, locale independence,
        the Org stub, the Markdown stub with a quoted title, the
        human-authored stub, and the invalid AI model;
      - from "pdf subcommand": job naming and missing page;
      - from "Pipeline helper module": both scenarios.
- [x] 2.2 Cover the `org-export` scenarios "Export plan" (all three,
      including the entries the validator does not examine) and
      "Exported timestamps" (all four) by running `pipeline.py
      export-plan` on temporary Org roots built from
      `tests/fixtures/valid/org/` and `tests/fixtures/org-invalid/`.
      Change only the keyword lines.
- [x] 2.3 `tests/test_pagefind_install.py` covers the four
      `install_pagefind` scenarios with tarballs built in the test. No
      network.
- [x] 2.3a `tests/test_export_replace.py` covers the `org-export` unit
      scenarios "Second rename fails", "Restore fails too" and "Backup
      deletion fails after a successful swap". They call `replace_export`
      and `recover_export` on temporary `build/` trees, injecting `rename`
      and `remove` functions that count their calls and raise `OSError` on
      the chosen one.
- [x] 2.4 `tests/test_site_config.py` covers these scenarios: "Hugo
      configuration", "Ignore rules", both "Caddyfile example" scenarios,
      and "Nothing enables the hook".
- [x] 2.5 `tests/test_samples.py` covers every `sample-procedures`
      scenario except "Review before archive" (manual) and "Clean
      validation of the shipped tree" (2.8):
      - sample procedures are discovered by the `sample-data` tag;
      - Org tables and Markdown pipe tables are parsed from source;
      - atomic weights and the CAS rule are as the spec states.
- [x] 2.6 `tests/test_build_script.py` (fish tests) covers these
      `build-script` scenarios: unknown subcommand, no subcommand, help,
      syntax and formatting, symlink invocation, Hugo missing, git
      missing although ox-hugo is installed (skip unless `.emacs-batch/`
      is bootstrapped), validate with arguments needing only Python,
      arguments passed through to the validator, both "clean" scenarios,
      and both "check-deps" scenarios.
- [x] 2.7 `tests/test_export_integration.py` covers every `org-export`
      integration scenario:
      - untouched `HOME` and inherited `TMPDIR`, using the read-only
        `TMPDIR`;
      - the pins and the pin mismatch;
      - seed export validating cleanly, the table guard, the AI model
        mapping, and surviving seconds;
      - literal text, braced subscripts, and unevaluated source blocks;
      - the orphan, the failed export, leftovers from a crashed run, and
        no sources;
      - both idempotence scenarios, including the named paragraph, and
        "Other sources do not change a file's anchors".
- [x] 2.8 `tests/test_build_integration.py` covers these integration
      scenarios:
      - every `site-build` integration scenario, including the
        future-dated and the expired procedure;
      - from `build-script`: "Seeds validate", "Invalid Markdown
        procedure", both "build subcommand" scenarios, "serve", both
        integration "pdf" scenarios, and "Hook refuses an invalid commit";
      - from `sample-procedures`: "Clean validation of the shipped tree".

      `serve` runs in its own process group, which the test kills in
      `tearDown`.
- [x] 2.9 Run `python3 -m pytest tests` and report which tests fail and
      which skip, with reasons. At this stage:
      - the change-1 suite stays green;
      - pure, configuration, sample and fish tests are red;
      - integration tests skip, because `.emacs-batch/` cannot be
        bootstrapped before `export.el` exists.

## 3. Python core (implementer)

- [x] 3.1 Add `tools/pipeline.py` (design.md D1) with the pure functions
      `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `export_instants`,
      `fill_template` and `pdf_jobs`. It reuses `validate.py`'s helpers,
      `discover` included. If `validate.py` must change to expose them, its specified
      behaviour and its suite must not change.
- [x] 3.2 Add the CLI subcommands `export-plan`, `next-id` and `new`
      (D3, D11). `export-plan` plans only the entries `validate.discover`
      returns as procedures. `new` scans the git history, falls back with
      a warning without git, and warns on a shallow clone.
- [x] 3.2a Add `recover_export` and `replace_export`, with injectable
      `rename` and `remove`, and the CLI subcommands `recover-export` and
      `install-export` (D4).
- [x] 3.3 Add `install_pagefind` and `ensure-pagefind` with the pinned
      URL and hashes (D8), and `pdf` with the WeasyPrint loop (D10).

## 4. Export (implementer)

- [x] 4.1 Add `tools/export.el` (D2–D6):
      - isolation settings before `(require 'package)` and before Org
        loads, `temporary-file-directory` and `TMPDIR` included;
      - the `package-vc-install` bootstrap and the pin check;
      - the bound-function check;
      - the table-order advice;
      - the body options;
      - the per-entry temporary-buffer export into the staging
        directory, with `(random "<stem>")` immediately before each
        export;
      - a non-zero exit with `export.el: <source>: <message>` on any
        error.

## 5. Site (implementer)

- [x] 5.1 Add `site/hugo.toml` exactly as design.md D7 gives it, and
      `site/content/_index.md` with the title `OrgSynDB`.
- [x] 5.2 Add `site/layouts/baseof.html`, `single.html` and `list.html`
      that satisfy the layout contract (D16) and nothing more.

## 6. Build script and companions (implementer)

- [x] 6.1 Add `tools/build.fish` with the conventions of D13, and the tool
      checks of the D12 preflight table, and `check-deps`.
- [x] 6.2 Implement the subcommands: `export` (recover, stage, then
      install through `pipeline.py`, D4),
      `validate` (D14), `build`, `serve` (D9), `pdf` (D10), `new` (D11)
      and `clean`. While bootstrapping, send Emacs output to
      `build/export.log`, and print it only on failure.
- [x] 6.3 Add `tools/hooks/pre-commit` (D15) and make it executable. Add
      `deploy/Caddyfile.example` (D15). Extend `.gitignore` with the D15
      entries.

## 7. Seed samples (implementer)

- [x] 7.1 Add `org/procedures/OSDB-0001-salicylic-acid.org` and
      `md/procedures/OSDB-0002-aspirin.md` as design.md D17 specifies:
      - quantities from the D17 table, all eight sections, numbered steps
        and notes;
      - the Vogel citation, with no page numbers;
      - real Europe/Berlin timestamps at the time of writing;
      - your own exact model identifier in `#+AI_MODEL` and `ai_model`.

      Use `tools/build.fish new` to create both stubs, then fill them.

## 8. Implementation verification (implementer)

- [x] 8.1 Run `tools/build.fish export` once to bootstrap `.emacs-batch/`
      (needs network). Then run `tools/build.fish build` to cache Pagefind.
- [ ] 8.2 Run `python3 -m pytest tests` until it is fully green with no
      integration test skipped on this machine, except the Caddy parse
      test, without editing any test. Return any test that looks wrong to
      the orchestrator.
- [x] 8.3 Run `openspec validate add-build-pipeline --strict`, and confirm
      that `git status` shows no generated file.
- [x] 8.4 List every document a person reads that this change affects,
      and what changed in it. Write none of them.

## 9. Manual verification (orchestrator)

Record each result in the review notes.

- [ ] 9.1 Brief §9 check 1: in a fresh clone in a temporary directory whose
      path contains a space, run `tools/build.fish check-deps`, then
      `tools/build.fish build`. Both succeed with no step beyond the
      printed `dnf` line, and the first run bootstraps ox-hugo, tomelr and
      Pagefind over the network.
- [ ] 9.2 Brief §9 check 6. Confirm that `python3 -m pytest tests` is
      green and that `tools/build.fish validate` passes on the seeds. Then
      run each committed fixture through the pass-through. Let `F` stand
      for `--vocabulary tests/fixtures/reaction_types.toml --static-dir
      tests/fixtures/static`, and run every command from the repository
      root. Confirm each scenario's field and message:
      - every `tests/fixtures/invalid/<case>` except `duplicate-id`, as
        its own single root: `tools/build.fish validate F
        tests/fixtures/invalid/<case>`. Each gives exactly one error.
      - `duplicate-id`, with both roots in one run:
        `tools/build.fish validate F tests/fixtures/invalid/duplicate-id/a
        tests/fixtures/invalid/duplicate-id/b`. This gives two `id`
        errors, each naming the other file. Run as a single root, the
        directory gives only two `subdirectories are not supported`
        errors and examines no file, which proves nothing.
      - every `tests/fixtures/warn/<case>`, as its own root. Each exits 0
        with exactly one warning.
      - the Org lint cases `missing-created`, `duplicate-created`,
        `active-timestamp`, `missing-seconds`, `invalid-date`,
        `wrong-weekday`, `nonexistent-local-time`,
        `last-modified-before-created`, `bad-ai-model`,
        `bad-org-file-name` and `subdirectory`, with the Org root only:
        `tools/build.fish validate F --org-root
        tests/fixtures/org-invalid/<case>/org`.
      - the cross-check cases `export-date-mismatch`,
        `export-offset-mismatch`, `export-ai-model-mismatch` and
        `missing-export`, with both roots: `tools/build.fish validate F
        --org-root tests/fixtures/org-invalid/<case>/org
        tests/fixtures/org-invalid/<case>/export`. `export-offset-mismatch`
        gives one error and one warning.
- [ ] 9.3 Brief §9 check 8: `tools/build.fish new "Manual check"` and
      `tools/build.fish new --md "Manual check"` create stubs with the next
      free IDs. The Org stub's `#+CREATED` is the current Europe/Berlin
      time with the right weekday, and `tools/build.fish validate` passes
      with both present. Delete both afterwards.
- [ ] 9.4 Brief §9 check 9: every Org file under `org/procedures/` and
      `templates/` carries the three keywords in the required format.
      Exported `date` and `lastmod` match them; the validator's
      cross-check passes in `build`.
- [ ] 9.5 Brief §9 check 10: a second `tools/build.fish build` succeeds.
      `sha256sum build/export/*` is unchanged across it, and `git status`
      stays clean.
- [ ] 9.6 Brief §9 check 2 (the part minimal layouts allow): run
      `tools/build.fish serve`. In a browser with the network panel open,
      the home page, a procedure page and a taxonomy page make zero
      requests to other hosts. Grep `public/` for `http://` and `https://`:
      only citation `<a href>` links and the Pagefind bundle's inert
      strings appear. A Pagefind search from the browser console
      (`await import("/pagefind/pagefind.js")`, then `search("aspirin")`)
      returns OSDB-0002. Ctrl-C stops the server.
- [ ] 9.7 Brief §9 check 7 (the part minimal layouts allow):
      `tools/build.fish pdf` writes one PDF per procedure, named
      `OSDB-NNNN-short-slug.pdf`. `pdfinfo` reports A4, and the PDFs carry
      no navigation chrome. Headers, footers and clipping are change 3's.
- [ ] 9.8 Fish behaviour that only a manual check covers:
      - the hook, enabled with `git config core.hooksPath tools/hooks` and
        then with a symlink, refuses a commit with an invalid procedure;
      - progress output reads cleanly in a terminal;
      - `check-deps` lines are correct on this machine.
- [ ] 9.9 Review each sample procedure for the "Benign textbook
      chemistry" requirement.

## 10. Documentation (orchestrator)

- [ ] 10.1 Hand README.md, docs/AUTHORING.md and docs/AUTHORING-ORG.org to
      the doc writer, as update or draft jobs. The facts each needs are
      listed in proposal.md Impact. The sources are this change's specs
      and design.md, `tools/build.fish help`, the templates, and the
      implementer's list from 8.4. Check each diff against those sources.
