## Context

Every integration test copies `examples/demo/` through
`make_sandbox`, and `ThemeBuildCase` and `BuildTestCase` call
`require_builder`, which requires `emacs`, `git` and the ox-hugo
checkout before Hugo and Pagefind. The demo holds four Org samples, so
every build exports them. The test collection removes that dependency
for every test whose assertion does not depend on an Org source being
exported.

## The sync rule

The test collection is only worth having while it says what the demo
says, so a test that needs no Emacs compares the two directly from
their sources.

- **Copies** are compared byte for byte: `orgsyndb.toml`, `.gitignore`,
  `static/` and the eight Markdown samples.
- **Converted samples** are compared field by field against the Org
  source, as `sample_support.read_org` already reads it: the
  custom-front-matter plist values, `#+TITLE`, `#+HUGO_SLUG`,
  `#+HUGO_TAGS` and `#+AI_MODEL`. Timestamps are compared as wall-clock
  time plus the Europe/Berlin offset, which is what the export writes,
  so the converted file has the dates its Org source would have
  exported.
- **Tables** are compared row by row through `table_rows`, because the
  Org table pads its cells and writes `+` in its separator line, which
  no text normalisation should have to know about.
- **Section text** is compared after collapsing whitespace and
  replacing each emphasis span by its inner text: Org spans as Org's
  emphasis syntax delimits them (marker after start, whitespace or
  `-('"{`, non-space just inside, closing marker before end,
  whitespace or `-.,:!?;'")}\[`), Markdown spans `**x**`, `*x*`,
  `` `x` `` and word-bounded `_x_`. Only delimiters go; every other
  character stays, so `C=O`, `C=C` and `E/Z-Verhältnis`, which occur in
  the samples, cannot drift to `CO`, `CC` or `EZ-Verhältnis`
  unnoticed, as they would if the marker characters were deleted
  everywhere. Under this rule each of the eight Org samples agrees with
  its current ox-hugo export in `examples/demo/build/export/` (heading
  anchors `{#…}` removed), in headings, Reagents rows and section text,
  so the rule accepts what the export itself writes. The one-off
  comparison of rendered pages in tasks.md section 5 still covers
  markup the rule does not model.

Rejected alternatives:

- *A test comparing the rendered HTML of a demo build and a test
  collection build.* It needs Emacs, so it would itself be an Org
  export test that skips exactly where the test collection is meant to
  help, and it doubles the build time of the suite. It is run once,
  by hand, when the collection is created.
- *Generating the test collection from the ox-hugo export.* The export
  needs Emacs, and its output differs in form from hand-written
  Markdown (`draft = false`, `{#summary}` heading anchors, inline
  arrays), so the collection would not be a collection of hand-written
  Markdown procedures like the demo's.
- *Comparing the converted files with the demo's `build/export/`.*
  That directory is generated and not committed, so the comparison
  would need Emacs too.

## Which tests keep the demo

A test keeps the demo when what it asserts depends on an Org source
being exported, and it then calls `require_exporter` itself. These are:

- every class of `tests/test_export_integration.py` (the export
  itself);
- `FixtureSiteTests.test_org_and_markdown_twins_render_alike`, which
  adds an Org fixture;
- "Org-sourced and Markdown-sourced pages" (site-build);
- "Second build without changes" (build-script), whose subject is a
  non-empty `build/export/`;
- "Clean validation of the shipped tree" (sample-procedures "Samples
  validate and export cleanly"), which validates the export of the
  shipped Org sources;
- "git missing although ox-hugo is installed" and "Emacs missing with
  Org sources", which need Org sources so that `export` asks for
  `emacs` and `git`, but no real Emacs.

`ExportWithoutOrgTests` and `CleanTests` also keep the demo, though
neither needs Emacs: the first empties a non-empty `org/procedures/`,
and the second checks that `clean` leaves `org/` alone, both of which
are vacuous on a collection without `org/`.

Four classes mix the two kinds and are split, because a class-level
`require_exporter` would skip their Markdown tests without Emacs:
`MergedSectionTests`, `BuildSubcommandTests`, `ValidateSubcommandTests`
and `FixtureSiteTests`. `FixtureSiteTests` keeps the twin test on the
demo; "A procedure without the tag has none" moves to a new class that
builds the test collection with `OSDB-0906-quoted-title.md`, at the cost
of one more Markdown-only build.

Rejected alternative: *keeping each class whole on the demo.* A class
builds or copies one collection for all its tests, so if that
collection is the demo, every test in the class needs Emacs, including
the ones that never look at an export.

## Tool scenarios without a real Emacs

Four scenarios put a real `emacs` on a test `PATH` without exporting
anything, so they skip without Emacs:

- "Hugo missing" needed `emacs` and `git` only because the demo has Org
  sources. On the test collection, `build` needs only `hugo`, so the
  `PATH` holds `python3` and the fake `sudo`.
- "Two tools missing" (check-deps) and "No Node in the tools"
  (site-search) only need `check-deps` to find `emacs` and `git`;
  `check-deps` probes with `shutil.which`, so the existing stub
  executables of `make_path` serve.
- "git missing although ox-hugo is installed" stops in `tools/orgsyndb`'s
  tool check, which also uses `shutil.which`, before any export starts.
  It keeps the demo, since without Org sources `export` would not ask
  for `git`, and puts a stub `emacs` on the `PATH`. It still skips
  without the ox-hugo checkout.

## Committed fixture IDs

The procedure-validation spec makes procedure IDs unique across
`tests/fixtures/`, and the test collection repeats the demo's IDs,
which `valid/` already uses for OSDB-0001 to OSDB-0004, and pairs each
sample with its German variant. The rule exempts `collection/`.
Renumbering the test collection was rejected: keeping the demo's IDs is
what lets the existing assertions about OSDB-0001, OSDB-0003, OSDB-0004
and the chains hold unchanged.

## Generated output under the fixture tree

The fixture identifier check reads every file under `tests/fixtures/`
and does not consult `.gitignore`. A run of `tools/orgsyndb` on
`tests/fixtures/collection` in place would write `build/` and `public/`
there, with absolute paths in the Hugo overlay and binary Pagefind
files, and fail that check. Both ends are closed:

- Nothing builds the test collection in place. Tests copy it through
  `make_sandbox`; the Pagefind skip hint names the demo build, or a
  build of a copy made elsewhere; the validation tasks build copies.
- The identifier check skips `collection/build/`, `collection/public/`
  and `collection/pdf/`, and still reads the collection's committed
  files, so a stray in-place build does not break the suite.

The test collection also carries the demo's `.gitignore`, so that such
a stray build stays out of `git status`. Rejected: pointing the hint at
an in-place build of the test collection, which is exactly what fails
the identifier check.

## Test helpers

- `TEST_COLLECTION = FIXTURES / "collection"` in `pipeline_support`.
- `require_builder()` requires `hugo` and the Pagefind cache only.
  `require_exporter()` is unchanged.
- `make_sandbox(case, *, collection=TEST_COLLECTION, copy_emacs=False,
  link_caches=True)` copies the named collection without its `build/`,
  `public/` and `pdf/`.
- `ThemeBuildCase` gains `COLLECTION = TEST_COLLECTION`, passed to
  `make_sandbox`; a subclass that exports sets `COLLECTION = DEMO` and
  calls `require_exporter()` from `require_tools`.
- `PAGEFIND_HINT` names a build that writes nothing under
  `tests/fixtures/`: the demo, or a copy of the test collection made
  elsewhere.
