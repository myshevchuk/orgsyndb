## MODIFIED Requirements

### Requirement: Metadata panel
The details wrapper at the start of `article.procedure` SHALL hold up to three widgets, in this order, each a `section.widget` whose `div.widget__head` holds its `h2` and whose `div.widget__body` holds one `dl.metadata`:
1. the compound widget, headed `Compound` when the procedure has one product and `Products` when it has several, holding the structure figures (requirement "Structure image slot") and the pairs `Product` or `Products`, `Formula`, `MW`, `CAS` and `SMILES`; it is always present;
2. the details widget, headed `Details`, holding the pairs `Reaction type`, `Tags`, `Authors`, `Checked by`, the declared procedure fields, `Created` and `Modified`, present when it has a pair;
3. the context widget, headed `Synthesis context`, holding the pairs `Starting materials`, `Precursors`, `Used in` and `Sequences`, present when it has a pair.

Each of the three `div.widget__head` carries `data-pagefind-ignore`, so that the widget titles are not indexed.

The metadata panel is the `dt`/`dd` pairs of these lists, read in document order. It holds one pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, the scale and yields are its key facts, and the checkers of a checked procedure are its sign-off. A compound's name is its shown name (localization "German compound names"). The compound widget's facts follow the order of the same facts in the lab's compound widget (lab-registry "Registry pages"): formula, molar mass, CAS number, SMILES.
- `Product`, or `Products` when the procedure has several: one `a.compound` per product, in `products` order, linking the substance's lab page `/lab/registry/substances/<key>/` (lab-registry "Registry pages") with the compound's name as text, each followed by its note of compound-fields "Values beside compound links" when it has one, joined by `, `;
- `Formula`, only when the procedure has one product: the compound's formula, where each digit run is wrapped in `<sub>`;
- `MW`, likewise, as `<mw> g/mol`;
- `CAS`, likewise, when the compound sets it;
- `SMILES`, likewise, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the account's name as text (procedure-authors "Author data for the site");
- `Checked by`, as the names joined by `, `, not linked, only when the status is not `checked`;
- each procedure field the collection declares (procedure-fields "Procedure field declarations") that the procedure sets, in declared order, labelled with the field's shown label (procedure-fields "Procedure field data"), its value written as compound-fields "Field display" writes a value, except that the journal field `notebook` (procedure-fields "Journal fields"), `<code>/<number>`, is a link to the lab's notebook page `/lab/journal/<code>/` with the value as text;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Starting materials`: one `a.compound` per entry of `substrates`, in its order, linking the compound's page with its name as text, each followed by its note as for `Product`, joined by `, `;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement;
- `Sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the widgets are headed `Compound`, `Details` and `Synthesis context`, and the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, then `Reaction type`, `Tags`, `Authors`, `Lab notebook`, `Project`, `Working time`, `Inert atmosphere`, `Created`, `Modified`, then `Starting materials`, `Precursors` and `Sequences`
- **AND** the values include an `a.compound` to `/lab/registry/substances/acetylsalicylic-acid/` with the text `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `a.compound` links `Salicylic acid` and `Acetic anhydride` under `Starting materials`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `Katrin Lehmann` and `Anna Schmidt` to `/authors/klehmann/` and `/authors/aschmidt/`, the texts `AE-1/2`, `Teaching › First-year practical`, `2.5 h` and `No`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, the declared procedure fields' shown labels standing in it, in declared order, between `Checked by` and `Created`; each label stands in the widget the requirement assigns it to; they include every label whose field the content file sets, except `Checked by` where the status is `checked`, with `Product` for one product and `Products` for several, and `Formula`, `MW` and `SMILES` exactly when there is one product, no page has an `ID`, `Scale` or `Yield` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure is linked
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and product name are both `Salicylic acid`, after a theme build
- **THEN** its panel's `Product` pair holds one `a.compound` to `/lab/registry/substances/salicylic-acid/` with the text `Salicylic acid`

#### Scenario: Panel of a procedure with two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure"
- **THEN** its compound widget is headed `Products` and its panel has a `Products` pair with the `a.compound` links `trans-Stilbene` and `cis-Stilbene`, in that order, and no `Product`, `Formula`, `MW`, `CAS` or `SMILES` pair

#### Scenario: Declared fields in the German panel
- **WHEN** a test reads `procedures/osdb-0002/index.html` of a build of the test collection in locale `de`
- **THEN** its panel holds the pairs `Laborjournal` `AE-1/2`, `Projekt` `Lehre › Grundpraktikum`, `Arbeitszeit` `2,5 h` and `Schutzgas` `Nein`, in this order, between the `Autoren` pair and the `Erstellt` pair

#### Scenario: Compound rows in the lab's order
- **WHEN** a test reads the compound widget of `procedures/osdb-0002/index.html` after a theme build in locale `en`, and the row labels of the template `webapp/registry/templates/registry/substance.html`
- **THEN** the procedure's labels `Formula`, `MW`, `CAS` and `SMILES` stand in the order of the substance page's rows `Formula`, `Molar mass`, `CAS number` and `SMILES`

#### Scenario: No context widget without links
- **WHEN** a test scans every procedure page after a theme build
- **THEN** a page has a context widget exactly when it has one of the pairs `Starting materials`, `Precursors`, `Used in` and `Sequences`, and every page has exactly one compound widget, first in the details wrapper

#### Scenario: The notebook links the journal
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build, whose procedure sets `notebook = "AE-1/2"`
- **THEN** the `Lab notebook` value is one link to `/lab/journal/AE-1/` with the text `AE-1/2`
