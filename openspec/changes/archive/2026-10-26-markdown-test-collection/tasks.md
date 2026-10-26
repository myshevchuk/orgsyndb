## 1. Tests

- [x] 1.1 In `tests/sample_support.py`, read the Org keywords a
  converted sample is compared with (`#+TITLE`, `#+HUGO_SLUG`,
  `#+HUGO_TAGS`, `#+AI_MODEL`, `#+CREATED`, `#+LAST_MODIFIED`), and
  add the agreement check of sample-procedures "Test collection": it
  takes an Org source and a Markdown procedure and returns the list of
  differences, empty when they agree.
- [x] 1.2 In `tests/test_samples.py`, add the test for "The agreement
  check (checker)", building both inputs in the test.
- [x] 1.3 In `tests/test_samples.py`, add the tests for "The test
  collection mirrors the demo" and "Converted samples agree with their
  Org sources", red: `tests/fixtures/collection/` does not exist yet.
- [x] 1.4 In `tests/test_fixture_suite.py`, leave `collection/` out of
  the unique-ID check, and leave `collection/build/`,
  `collection/public/` and `collection/pdf/` out of the identifier
  check while it still reads the collection's committed files. Name
  the scenarios "Committed IDs are unique" and "Committed fixtures
  carry no identifiers" in the docstrings.

## 2. Test collection

- [x] 2.1 Create `tests/fixtures/collection/` with byte-identical
  copies of the demo's `orgsyndb.toml`, `.gitignore` and
  `static/structures/osdb-0003.svg`, and no `org/`.
- [x] 2.2 Copy the demo's eight Markdown samples (OSDB-0002, 0005,
  0006, 0008 and their `.de` variants) byte for byte into
  `md/procedures/`.
- [x] 2.3 Convert the eight Org samples (OSDB-0001, 0003, 0004, 0007
  and their `.de` variants) to `md/procedures/<stem>.md` in the form of
  the demo's Markdown samples: the front-matter keys in the order of
  OSDB-0005, with `structure_image` after `references` and
  `[product]` last; `date` and `lastmod` from `#+CREATED` and
  `#+LAST_MODIFIED` with the Berlin offset; `##` headings; pipe tables
  with `|---|` separators; `*text*` for `/text/`.
- [x] 2.4 Run the tests of section 1 green, and
  `tools/orgsyndb -C <copy> validate` on a copy of the collection made
  outside `tests/fixtures/`, with no problem line. Nothing runs
  `tools/orgsyndb` on `tests/fixtures/collection` in place.

## 3. Moving the tests

- [x] 3.1 In `tests/pipeline_support.py`: add `TEST_COLLECTION`; make
  `require_builder` require only `hugo` and the Pagefind cache; give
  `make_sandbox` a `collection` parameter defaulting to
  `TEST_COLLECTION`; give `ThemeBuildCase` a `COLLECTION` attribute
  defaulting to `TEST_COLLECTION`; keep `PAGEFIND_HINT` naming a
  build that writes nothing under `tests/fixtures/`: `tools/orgsyndb
  -C examples/demo build`, or, without Emacs, a build of a copy of the
  test collection made elsewhere; update the module docstring.
- [x] 3.2 Classify every class that copies a collection, as below.
  "Moves" means it uses the test collection and needs no Emacs.
  "Stays" means it passes `DEMO` explicitly, and calls
  `require_exporter` where it exports.
  - `tests/test_theme_integration.py`
    - `ShippedSiteTests`: moves.
    - `FixtureSiteTests`: stays, with `COLLECTION = DEMO` and
      `require_exporter`; keeps only "Twin fixtures".
    - New class building the test collection with
      `OSDB-0906-quoted-title.md`: takes "A procedure without the tag
      has none".
  - `tests/test_localization_integration.py`
    - `GermanSiteTests`: moves; its docstring names "Choosing the
      variant to publish (test collection)".
    - `PartialTranslationTests`: moves; removes
      `md/procedures/OSDB-0001-salicylic-acid.de.md` and
      `md/procedures/OSDB-0004-4-acetylbiphenyl.de.md`.
    - `GermanPdfTests`: moves.
  - `tests/test_print_integration.py`
    - `PdfBuildTests`, `PdfSiteUrlTests`: move.
    - `HiddenOverflowTests`: copies no collection; unchanged.
  - `tests/test_search_integration.py`
    - `ShippedSearchTests`: moves.
  - `tests/test_build_integration.py`
    - `MergedSectionTests`: split. "Org-sourced and Markdown-sourced
      pages" stays, with `require_exporter`; "Future-dated procedure
      is published, indexed and printed", "Expired procedure is still
      published" and "Stray file and section index are not published"
      move.
    - `LayoutContractTests`, `NoRemoteFetchTests`, `SearchIndexTests`:
      move.
    - `BuildSubcommandTests`: split. "Validation error stops the build
      before Hugo" moves; "Second build without changes" stays, with
      `require_exporter`.
    - `ValidateSubcommandTests`: split. "Seeds validate" and "Invalid
      Markdown procedure" move; "Clean validation of the shipped tree"
      stays, with `require_exporter`.
    - `ServeTests`, `PdfTests`, `HookTests`, `CollectionBuildTests`:
      move.
    - The module docstring no longer says the tests need Emacs.
  - `tests/test_build_script.py`
    - `UsageTests`, `ValidateArgumentTests`: move; they need no tool.
    - `MissingToolTests`: "Hugo missing" moves, with a `PATH` of
      `python3` alone; "git missing although ox-hugo is installed"
      stays on the demo and puts a stub `emacs` on the `PATH` instead
      of the real one; "Emacs missing with Org sources" stays and needs no
      Emacs; "Markdown-only collection builds without Emacs and git"
      moves and no longer empties `org/procedures/` or strips
      `precursors`.
    - `CleanTests`: stays, without `require_exporter`.
    - `CheckDepsTests`: "Two tools missing" puts stub `emacs` and
      `git` on the `PATH`.
  - `tests/test_theme_static.py`
    - `NoNodeInToolsTests`: the check-deps test puts stub `emacs` and
      `git` on the `PATH`.
  - `tests/test_export_integration.py`
    - `IsolationTests`, `PinTests`, `OldEmacsTests`,
      `ExportedFrontMatterTests`, `BodyOptionTests`,
      `FreshExportDirectoryTests`, `IdempotenceTests`: stay, with
      `require_exporter` as now.
    - `ExportWithoutOrgTests`: stays, without `require_exporter`.
    - `NoPackageElTests`: copies no collection; unchanged.

## 4. Documentation

- [x] 4.1 README Development section: the integration tests build the
  test collection and need no Emacs; only the Org export tests need
  Emacs, git and the ox-hugo cache. The Pagefind cache comes from
  building the demo, or, without Emacs, a copy of the test collection
  made outside `tests/fixtures/`; the test collection is never built in
  place. Written by the doc stage.

## 5. Validation

- [x] 5.1 Build copies of `examples/demo` and
  `tests/fixtures/collection`, made outside `tests/fixtures/`, in
  locales `en` and `de`, and check that the pages of the four
  converted procedures are byte-identical between the two builds.
- [x] 5.2 Run the full suite with `emacs` on `PATH`; it passes.
- [x] 5.3 Run the full suite with `pytest -rs` and a `PATH` that finds
  every tool the suite uses except `emacs`, for example a directory of
  symlinks to the original `PATH`'s executables without `emacs`. It
  passes, and every skip listed is a test of section 3.2 that stays
  and calls `require_exporter`, each with the reason `emacs not
  found`.
- [x] 5.4 Run `openspec validate markdown-test-collection --strict`.
