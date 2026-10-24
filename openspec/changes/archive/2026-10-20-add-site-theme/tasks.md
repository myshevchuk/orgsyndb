## 1. Fixtures and harness (test writer)

House rules for the tests:

- Tests are `unittest.TestCase` classes, named for behaviour and run with
  `python3 -m pytest tests`.
- Tests locate the repository from their own `__file__`.
- Paths are passed as list arguments, never through a shell string.
- Names are fictitious, and no user or machine identifier appears.
  The repository has a public remote.

The terms "theme build", "PDF build", "search test", "scan", "page text"
and `N(s)` are defined in the spec comments. The test layers and skips are
in design.md D17. Integration tests skip only for a missing tool or cache,
naming it; they never skip for any other reason.

- [x] 1.1 Add `tests/fixtures/theme/OSDB-0904-twin.org` and
      `tests/fixtures/theme/OSDB-0905-twin.md` (design.md D16). They are
      fully valid procedures with identical content, apart from `id` and
      `slug`:
      - the title `Twin product`;
      - `#+CREATED: [2026-10-20 Tue 09:00:00]` and
        `#+LAST_MODIFIED: [2026-10-20 Tue 09:30:00]`; the Markdown file
        has `date = 2026-10-20T09:00:00+02:00` and
        `lastmod = 2026-10-20T09:30:00+02:00`;
      - `#+AI_MODEL: example-model-1`, and `ai_model = "example-model-1"`;
      - `authors = ["A. Example"]`, `checked_by = ["D. Example"]`, tags
        `sample-data` and `twin-check`, `reaction_types =
        ["esterification"]`, and `precursors = ["OSDB-0001"]`;
      - a product with every key (for example ethyl acetate, CAS
        `141-78-6`);
      - all eight sections, a six-column Reagents table, numbered steps
        and notes, italic, bold, and `H_{2}O` (Org) /
        `H<sub>2</sub>O` (Markdown);
      - identical line breaks in every paragraph and list item.
- [x] 1.2 Add `tests/fixtures/theme/OSDB-0906-quoted-title.md`. It is a
      fully valid Markdown procedure titled `Bob's "best" </style> ester \ x`
      (a TOML basic string with escapes), with tags `banner-check` only,
      so no `sample-data`.
- [x] 1.2a Add `tests/fixtures/theme/clip-negative-control.html`
      (design.md D12). It is a standalone HTML page with an inline
      `@page { size: A4; margin: 16mm }` and a visible paragraph, then
      `<div style="height:1px; overflow:hidden">` around two paragraphs,
      the first containing the word `HiddenClippedSentinel`, then another
      visible paragraph. It has no remote reference.
- [x] 1.3 Extend `tests/pipeline_support.py` with:
      - a helper that copies named files from `tests/fixtures/theme/` into
        the sandbox's `org/procedures/` or `md/procedures/` by suffix;
      - an HTML page model built with `html.parser`. It gives:
        - the indexed body's text;
        - the `dt`/`dd` pairs, with raw HTML between `</dt>` and `<dd>`;
        - elements by class;
        - links with resolved targets;
        - `data-pagefind-filter` and `data-pagefind-meta` elements with
          their text;
        - headings in order;
        - tables as cell lists with their classes;
        - stylesheet links with `media`;
        - `script` sources;
        - `button` attributes;
      - `serve_directory(path)`, a context manager running a
        `ThreadingHTTPServer` with `SimpleHTTPRequestHandler` on
        `127.0.0.1` and a free port in a daemon thread, yielding the base
        URL;
      - `pagefind_search(public, requests)`. It skips unless `node`
        exists. It copies `public/pagefind/pagefind.js` to a temporary
        `pagefind.mjs`, serves `public/`, runs
        `node tests/js/pagefind-query.mjs` with the JSON requests on
        stdin, and returns the parsed stdout;
      - PDF helpers that skip unless `pdfinfo` and `pdftotext` exist.
        They give the page count and page size from `pdfinfo`, the
        per-page `-layout` and `-raw` texts, and the per-page word boxes
        from `-bbox` (page width and height, and `xMin`, `xMax` per word).
        The skip reason names the tool and says `poppler-utils`.
      - a CSS declaration parser for the source stylesheets and for
        inline `style` attributes (selector → declarations, including
        inside `@media` and `@page`), and a WCAG contrast function;
      - the clipping-CSS check of print-layout "No clipping CSS in print",
        as a function over parsed declarations, so that the static test
        and the negative-control test share it.
- [x] 1.4 Add `tests/js/pagefind-query.mjs`, a test-only Node script
      (design.md D15). It is invoked as `node pagefind-query.mjs
      <pagefind.mjs> <bundle base URL> <search-terms.js>`.
      - It imports both scripts and sets `basePath`.
      - For each stdin request `{"term", "filters", "normalise"}`, it
        calls `search`. The term is normalised with
        `OrgSynSearch.normaliseTerm` when `normalise` is true, and `null`
        is allowed.
      - It prints JSON `{"results": [[{"id", "title", "excerpt",
        "meta"}...]...], "filters": <filters()>}`.
      - It exits non-zero on any error.

## 2. Failing tests (test writer)

Write each test so that, once the theme exists, it fails on its assertion
and not on an import or setup error. Build once per test class.

- [x] 2.1 `tests/test_theme_static.py`: static tests that need no build.
      They cover the scenarios "Dark mode only on screen", "Contrast in
      both schemes", "Shipped structure images", "Print colours",
      "Declarations present" and "No clipping CSS in print"
      (print-layout), and "No Node in the tools"
      (the file search; the `check-deps` half uses the fish-test `PATH`
      helper and skips without fish).
- [x] 2.2 `tests/test_theme_js.py` (skips without `node`): "Normalised
      terms" and "Cleaned result".
- [x] 2.3 Extend `tests/test_samples.py` with the sample-procedures
      scenarios "Set, counts and chain", "Structure image is set" and
      "Long sample". The existing sample tests must keep passing over all
      eight samples.
- [x] 2.4 `tests/test_theme_integration.py` (theme build). It covers
      every site-theme scenario that is not marked as manual verification:
      - "No third-party theme and no web fonts" and "Only external, local
        scripts";
      - "Shell on every page" and "Term titles use labels and tags";
      - "Three links on every page";
      - "Reagents tables are wrapped and marked";
      - "Header and body in order";
      - both metadata-panel scenarios;
      - "Links resolve in both directions" and "The shipped chains";
      - both banner scenarios, the second with the quoted-title fixture;
      - "Image and placeholder";
      - "Both orders" and "Home page content";
      - "Every term page lists the right procedures";
      - "Static HTML holds the content";
      - "Twin fixtures";
      - print-layout "The URL is text only", which needs only the theme
        build.

      It also covers the site-search static scenarios: "Search page
      wiring", "Metadata inside the body, chrome outside", "Filter
      attributes on every procedure page", "Index value" and "Index on
      every procedure page".
- [x] 2.5 `tests/test_search_integration.py` (theme build plus Node). It
      covers "CAS numbers are separate words", "Filter values and
      filter-only searches", "Result data", "Name, CAS, tag, ID and body
      word", "Every SMILES substring" and "Full SMILES is exact". Batch
      all queries of a class into one Node run.
- [x] 2.6 `tests/test_print_integration.py` (PDF build). It covers every
      print-layout scenario not marked manual and not covered by 2.1:
      - "A4 PDFs";
      - "Header and footer on every page" and "Title with quotes and
        markup characters";
      - "No chrome in the PDFs";
      - "Full URL on the first page by default" and "Site URL from the
        environment",
        the latter a separate PDF build with `HUGO_PARAMS_SITEURL` set
        through `Sandbox.env`;
      - "No page ends on a heading" and "Steps and rows stay on one page";
      - "Every word within the margins", "Every table cell is printed"
        and "The long sample spans pages";
      - "The checks do not see hidden overflow". This needs WeasyPrint and
        poppler but no build: render the fixture of 1.2a into a temporary
        directory. Assert that the margin and text checks pass and the
        clipping-CSS check fails, and say in the docstring that this
        records the checks' limit. Do not "fix" it into a failing test;
      - "Clean pdf run".
- [x] 2.7 Update `tests/test_build_integration.py` for the MODIFIED
      scenarios:
      - "One indexed body per procedure page": every procedure page has
        a body, derived from the content files' slugs instead of the two
        seed slugs;
      - "One PDF per procedure, no stale files": the expected PDF names
        are the content files' stems, and the two seed names are
        asserted to be among them.

      Update `tests/test_site_config.py` for the MODIFIED "Hugo
      configuration": `keepWhitespace`, `params.siteurl` equal to
      `http://127.0.0.1:8000`, and the host check, which now allows
      exactly that one string.
- [x] 2.8 Run `python3 -m pytest tests` and report which tests fail and
      which skip, with reasons. At this stage:
      - the change-1 and change-2 suites stay green, apart from the
        updated scenarios in 2.7 and the config test;
      - every new test is red;
      - nothing skips on this machine except the Caddy parse test.

## 3. Site configuration and content (implementer)

- [x] 3.1 Add `[minify.tdewolff.html]` with `keepWhitespace = true`
      (design.md D6) and `[params]` with `siteurl = "http://127.0.0.1:8000"`
      (D11) to `site/hugo.toml`. Change nothing else in the file.
- [x] 3.2 Add `site/content/search.md` (`title = "Search"`,
      `layout = "search"`), `site/content/procedures-by-date.md`
      (`title = "All procedures by date"`, `layout =
      "procedures-by-date"`), `site/content/procedures/_index.md`
      (`title = "All procedures"`) and
      `site/content/reaction_types/_index.md` (`title = "Reaction types"`)
      (D1).

## 4. Layouts (implementer)

- [x] 4.1 Rewrite `site/layouts/baseof.html` as the page shell (site-theme
      "Page shell"; D1, D2). Keep a literal `<head>` line. It links the
      three stylesheets and `site.js`, and gives the `head` and `scripts`
      blocks. Remove `list.html` and `single.html`.
- [x] 4.2 Add the partials listed in D1. Put a newline between every
      `</dt>` and `<dd>`.
- [x] 4.3 Add `site/layouts/procedures/page.html` (D1, D6–D11, D14):
      - the banner, the header, the print facts and the hidden print
        button;
      - the body with the panel, the structure figure, the content and the
        SMILES index span;
      - the inline `@page` style in the `head` block.
- [x] 4.4 Add `home.html`, `section.html`, `procedures-by-date.html`,
      `taxonomy.html`, `term.html`, `search.html` and `page.html` (D1, D4,
      D5).
- [x] 4.5 Add `site/layouts/_markup/render-table.html` (site-theme
      "Measure, responsiveness and tables"; D11).

## 5. Stylesheets and scripts (implementer)

- [x] 5.1 Add `site/assets/css/tokens.css`, `base.css`, `screen.css` and
      `print.css` (D2, D3, D11). Use only CSS that WeasyPrint 70.0 accepts
      in `tokens.css`, `base.css` and `print.css`. Keep screen-only
      properties and the dark tokens in `screen.css`. In the three
      print-applicable files, declare no `overflow`/`overflow-x`/
      `overflow-y` of `hidden` or `clip`, and no `height`/`max-height`
      other than `auto` or `none`, except `max-height` on `img`
      (print-layout "Nothing is clipped"). So no visually-hidden helper
      either.
- [x] 5.2 Add `site/assets/js/site.js`: print button, copy button with
      the selection fallback, and the text of `span.page-url` (site-theme
      "Content does not need JavaScript"). Only the Print and Copy
      buttons start `hidden`; the home search submit button never does.
- [x] 5.3 Add `site/assets/js/search-terms.js`, a classic script, and
      `site/assets/js/search.js` (site-search "Query normalisation" and
      "Search page"; D5, D7). The search page loads them as one
      concatenated, minified, fingerprinted bundle.

## 6. Structure image and samples (implementer)

- [x] 6.1 Hand-write `site/static/structures/osdb-0003.svg` (D14).
- [x] 6.2 Create the six samples with `tools/build.fish new`, in ID
      order, passing `--ai-model` with your own exact model identifier.
      The titles below give the file names the sample-procedures spec
      requires:
      - Org: `Isopentyl acetate`, `4-Acetylbiphenyl`,
        `1-(Biphenyl-4-yl)ethanol`, `Dibenzylideneacetone`,
        `Ethyl cinnamate`;
      - then `--md` `Cinnamic acid` (OSDB-0008).

      Fill them as design.md D13 specifies:
      - the products, reaction types, precursors and tags of the D13
        table;
      - the Reagents tables exactly as given, or recomputed so that the
        sample-procedures quantity rules still hold;
      - all eight sections;
      - the Summary's "not experimentally verified" sentence;
      - Vogel as the reference, plus the two optional citations only if
        flagged for the orchestrator's check;
      - no literature value that cannot be checked;
      - in the Org files, `:structure_image` (OSDB-0003) on a
        custom-front-matter line before `:product`.

      Make OSDB-0004 the long sample. Every sample's `Procedure` section
      must contain a word of six or more letters found in no other
      sample's file (site-search "Name, CAS, tag, ID and body word").

## 7. Implementation verification (implementer)

- [x] 7.1 Run `tools/build.fish build` and `tools/build.fish pdf`. The
      validator prints `validated 14 files: 0 errors, 0 warnings`, and
      the `pdf` output contains no `WARNING:` line.
- [x] 7.2 Run `python3 -m pytest tests` until it is fully green, with no
      test skipped on this machine except the Caddy parse test, and
      without editing any test. Return any test that looks wrong to the
      orchestrator.
- [x] 7.3 Run `openspec validate add-site-theme --strict`, and confirm
      that `git status` shows no generated file and that no committed
      file carries a user or machine identifier (`grep -rn "/home/"` over
      the changed files).
- [x] 7.4 List every document a person reads that this change affects,
      and what changed in it. Write none of them.

## 8. Chemistry review (orchestrator)

- [x] 8.1 Review each new sample for the "Benign textbook chemistry"
      requirement:
      - reagents, conditions and hazards;
      - each product and reagent CAS number resolving on PubChem as a
        name, for example
        `curl -s "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/140-10-3/property/Title,MolecularFormula/JSON"`
        (a cross-reference listing alone does not count; design.md D13);
      - each citation.

      Drop either optional citation of design.md D13 that cannot be
      confirmed.

## 9. Manual verification (orchestrator)

Work in the repository root, in fish. Let `S` be a scratch directory
outside the repository: `set S (mktemp -d)`. Record each result in the
review notes, and delete `S` afterwards.

- [x] 9.1 Brief §9 check 2, zero external requests:
      1. Run `tools/build.fish serve` in one terminal, and wait for
         `serving http://127.0.0.1:8000/ (Ctrl-C to stop)`.
      2. The printed page URL is text, once per procedure page (design.md
         D11). Count it:
         `grep -rIhoE 'http://127\.0\.0\.1:8000/procedures/osdb-[0-9]{4}/' public | sort -u | wc -l`
         prints 8. Then list every other absolute URL in the build:
         `grep -rIhoE 'https?://[^"'"'"' <>)]+' public | grep -vxE 'http://127\.0\.0\.1:8000/procedures/osdb-[0-9]{4}/' | sort | uniq -c`.
         Only citation links (if any) and the Pagefind bundle's inert
         strings may appear:
         - translator credit URLs in `pagefind-ui.js` and
           `pagefind-component-ui.js`;
         - `http://www.w3.org/2000/svg` inside `data:` URLs;
         - two browser bug-tracker links in a CSS comment.
      3. Check that none of them, the page URL included, is in a
         fetching position:
         `grep -rIlE '(src|srcset|poster|data)=("|)?(https?:)?//|<link[^>]+href=("|)?(https?:)?//|url\(("|'"'"')?(https?:)?//|@import[^;]*(https?:)?//' public`
         prints nothing.
      4. In Firefox, with the network panel open and the cache disabled,
         load `/`, `/procedures/osdb-0004/`, `/procedures-by-date/`,
         `/reaction_types/olefination/`, `/tags/biphenyl/`,
         `/authors/a.-example/` and `/search/?q=aspirin`. Every request
         goes to `127.0.0.1:8000`, and none fails.
- [x] 9.2 Brief §9 check 3, search, in Firefox on `/search/`. Type each
      query into the box and confirm the result list.
      1. Each sample by:
         - product name: `Isopentyl acetate`, `4-acetylbiphenyl`,
           `ethyl cinnamate`;
         - CAS: `92-91-1`, `3562-73-0`, `103-36-6`, `140-10-3`,
           `69-72-7`;
         - SMILES substring. Expected sets are the samples whose normalised
           SMILES contains the normalised query, computed over all eight
           (design.md D7):
           - `c1ccccc1O` → OSDB-0001 only;
           - `ccc(cc1)-c1` → OSDB-0004 and 0005;
           - `CC(C)CCO` → OSDB-0003 only;
           - `O=C(/C=C/c1` → OSDB-0006 only;
           - `CCOC(=O)/C=C` → OSDB-0007 only;
           - `OC(=O)/C=C/c1` → OSDB-0007 and 0008.

           Cinnamic acid's normalised SMILES is a suffix of ethyl
           cinnamate's, so no SMILES query finds OSDB-0008 alone;
         - tag: `suzuki-coupling`, `wittig`, `claisen-schmidt`,
           `cinnamate` (OSDB-0007 and 0008);
         - body word: `wintergreen` (OSDB-0001).

         No excerpt shows a run of SMILES fragments, and each result
         shows "Id: OSDB-…".
      2. Filters. Search `sample`; eight results.
         1. Open "Reaction type" and tick "Olefination": one result,
            OSDB-0007. Untick it.
         2. Tick "Esterification", then also "Hydrolysis": the results
            go to zero (AND within a group, design.md D5). Untick both.
         3. Open "Tag" and tick `cinnamate`: OSDB-0007 and 0008.
         4. Also tick "Reaction type → Hydrolysis": only OSDB-0008.
            Untick all.
         5. Tick `biphenyl`: OSDB-0004 and 0005. Untick it.
         6. Open "Status" and tick `draft`: all eight.
         7. Open "Author", tick one name, and compare the results with
            that author's `/authors/<name>/` page.
      3. Keyboard: reload `/search/?q=aspirin`. Using Tab, Shift-Tab and
         Space only, reach the input, each filter group, a checkbox (tick
         it), and a result link (Enter opens it). A focus outline is
         visible at every stop.
      4. No JS: disable JavaScript (`about:config` →
         `javascript.enabled` false), load `/search/` and see the
         `noscript` links. Load `/procedures/osdb-0004/`: the content is
         complete, and the Print and Copy buttons are absent. On `/`, the
         search form's Search button is visible; submitting `aspirin`
         loads `/search/?q=aspirin` with the `noscript` text. Re-enable
         JavaScript.
- [x] 9.3 Brief §9 check 4, taxonomy pages and source parity:
      1. Open `/reaction_types/`, `/tags/` and `/authors/`. Every term
         shows its label or name and a count.
      2. For each term, compare its page with
         `grep -l '<term>' org/procedures/*.org md/procedures/*.md`, in
         the form `:reaction_types '("<slug>")`, `#+HUGO_TAGS:` or
         `authors =`. The listed IDs must match.
      3. Open `/procedures/osdb-0001/` (Org) and `/procedures/osdb-0002/`
         (Markdown) side by side. Their layouts are indistinguishable.
      4. Confirm that `tests/test_theme_integration.py`'s twin test
         passed.
- [x] 9.4 Brief §9 check 5, precursor and used-in links, for each chain
      OSDB-0001 → 0002, OSDB-0004 → 0005 and OSDB-0007 → 0008:
      1. On the first procedure's page, follow "Used in" to the second.
      2. On the second's page, follow "Precursors" back to the first.
      3. Every link lands on the named procedure, and no other procedure
         lists a precursor or used-in.
- [x] 9.5 Brief §9 check 7, PDFs:
      1. Run `tools/build.fish pdf`. It exits 0, prints one `pdf:` line
         per procedure (eight), and prints no `WARNING:` line.
      2. Run `ls pdf`: exactly the eight `OSDB-NNNN-short-slug.pdf`
         names.
      3. For each file, `pdfinfo pdf/<name>` reports
         `595.276 x 841.89 pts (A4)`.
      4. `for f in pdf/*.pdf; pdftotext -layout "$f" - | grep -cE 'Page [0-9]+ of [0-9]+'; end`
         prints each PDF's page count.
      5. `pdftotext -layout pdf/OSDB-0004-4-acetylbiphenyl.pdf - | head -3`
         shows `OSDB-0004` with the title on the first line.
      6. Render page images:
         `pdftoppm -r 70 -png pdf/OSDB-0004-4-acetylbiphenyl.pdf "$S/p0004"`,
         `pdftoppm -r 70 -png pdf/OSDB-0003-isopentyl-acetate.pdf "$S/p0003"`
         and `pdftoppm -r 70 -png pdf/OSDB-0008-cinnamic-acid.pdf "$S/p0008"`.
         This raster review is the acceptance evidence for "nothing
         clipped". The automated checks cannot see content hidden inside
         its own box (print-layout "Nothing is clipped"; design.md D12).
         On every page image check:
         - the running header (ID left, title right) and
           "Page N of M";
         - black on white, the banner box, and the first-page line
           beginning `http://127.0.0.1:8000/procedures/osdb-…/`, with ID,
           status and modified date;
         - no navigation, buttons or placeholder;
         - nothing cut off at a box or page edge: no half-visible line,
           table, figure or rule;
         - the Reagents table inside the margins, with numbers unbroken;
         - no heading at the foot of a page;
         - the SVG structure on OSDB-0003.
      7. Run
         `env HUGO_PARAMS_SITEURL=https://orgsyndb.example.invalid tools/build.fish pdf`,
         then `pdftotext -l 1 pdf/OSDB-0002-aspirin.pdf - | grep orgsyndb.example.invalid`.
         It shows the absolute URL. Run `tools/build.fish pdf` again
         without the variable.
      8. Browser fallback: in Firefox, print `/procedures/osdb-0004/` to
         a PDF in `S` on A4, and render it with `pdftoppm`. Check it as
         in step 6, without the running header and page numbers, which
         Firefox omits (print-layout "Browser print fallback").
- [x] 9.6 Visual review of the rendered pages. Take headless Firefox
      screenshots with throwaway profiles:
      1. Make the profiles:
         `mkdir "$S/light" "$S/dark"; echo 'user_pref("ui.systemUsesDarkTheme", 0);' > "$S/light/user.js"; echo 'user_pref("ui.systemUsesDarkTheme", 1);' > "$S/dark/user.js"`
      2. For each of `/`, `/procedures/`, `/procedures-by-date/`,
         `/procedures/osdb-0003/`, `/procedures/osdb-0004/`,
         `/reaction_types/` and `/tags/biphenyl/`, run
         `firefox --headless --no-remote --profile "$S/light" --window-size=1100,1600 --screenshot "$S/<name>-light.png" http://127.0.0.1:8000<path>`.
         Repeat with `--profile "$S/dark"`, and with
         `--window-size=390,1600` for the phone width.
      3. Review each image:
         - light and dark both legible;
         - the structure image on its white panel in dark mode;
         - about 70 characters per line on wide screens;
         - no sideways page scroll at 390 px;
         - the long Reagents table scrolling inside its box;
         - status badges and the banner distinct;
         - heading order sensible.

      Search results render after the screenshot is taken, so review
      `/search/` in the interactive browser of 9.2. An agent can instead
      script it with a throwaway WebDriver BiDi client against
      `firefox --headless --remote-debugging-port`, kept out of the
      repository (design.md Verification).
- [x] 9.7 Copy button: on `http://127.0.0.1:8000/procedures/osdb-0002/`,
      Copy places `CC(=O)Oc1ccccc1C(=O)O` on the clipboard and the label
      changes. The Print / Save as PDF button opens the print dialog.

## 10. Documentation (orchestrator)

- [ ] 10.1 Hand README.md, docs/AUTHORING.md and docs/AUTHORING-ORG.org
      updates to the doc writer.
      - The facts each needs are listed in proposal.md Impact. The
        sources are this change's specs and design.md, the earlier
        changes' archived design.md files, `tools/build.fish help`, the
        templates, and the implementer's list from 7.4.
      - Check each diff against those sources, and confirm that no
        committed document carries a user or machine identifier.
