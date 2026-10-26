## Why

A collection without Org procedures builds without Emacs, but the
Python test suite still needs Emacs almost everywhere: every
integration test that builds, validates, serves or prints a site
copies the demo collection, whose Org procedures go through the
export. Only the tests that exercise the Org export should need it.

## What Changes

- A new Markdown-only test collection, `tests/fixtures/collection/`,
  holds all eight sample procedures and their German variants under
  the demo's file names: the four Markdown samples copied byte for
  byte, the four Org samples converted to hand-written Markdown with
  the same content. Its structure images, `orgsyndb.toml` and
  `.gitignore` are copies of the demo's.
- A sync test that needs no Emacs keeps the test collection in step
  with the demo: copies stay byte-identical, and each converted
  procedure keeps its Org source's front matter, timestamps, headings,
  Reagents rows and section text.
- Integration tests that do not exercise the Org export build, validate,
  serve and print the test collection. Tests that do exercise it keep
  the demo and keep requiring Emacs.
- Tool scenarios that needed a real Emacs without exporting anything
  use the test collection or stub executables instead.
- With `emacs` absent from `PATH`, the full suite passes, and only the
  tests that exercise the Org export skip, naming `emacs`.

## Impact

Affects the sample-procedures, site-build, localization, build-script,
site-search and procedure-validation capabilities; adds
`tests/fixtures/collection/`; changes `tests/pipeline_support.py`,
`tests/sample_support.py` and the integration test modules
(`test_build_integration.py`, `test_build_script.py`,
`test_theme_integration.py`, `test_theme_static.py`,
`test_localization_integration.py`, `test_print_integration.py`,
`test_search_integration.py`, `test_samples.py`,
`test_fixture_suite.py`); and the README's Development section, which
says the integration tests need Emacs. No production code changes.
