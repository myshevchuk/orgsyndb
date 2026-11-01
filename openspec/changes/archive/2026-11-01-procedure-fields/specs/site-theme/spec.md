## MODIFIED Requirements

### Requirement: Metadata panel
The metadata panel SHALL be a `dl.metadata`, the first element of the details wrapper at the start of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, the scale and yields are its key facts, and the checkers of a checked procedure are its sign-off. A compound's name is its shown name (localization "German compound names").
- `Product`, or `Products` when the procedure has several: one `a.compound` per product, in `products` order, linking `/compounds/<key>/` with the compound's name as text, joined by `, `;
- `Formula`, only when the procedure has one product: the compound's formula, where each digit run is wrapped in `<sub>`;
- `MW`, likewise, as `<mw> g/mol`;
- `CAS`, likewise, when the compound sets it;
- `SMILES`, likewise, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Starting materials`: one `a.compound` per entry of `substrates`, in its order, linking the compound's page with its name as text, joined by `, `;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the name as text;
- `Checked by`, as the names joined by `, `, not linked, only when the status is not `checked`;
- each procedure field the collection declares (procedure-fields "Procedure field declarations") that the procedure sets, in declared order, labelled with the field's shown label (procedure-fields "Procedure field data"), its value written as compound-fields "Field display" writes a value on a compound page;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement;
- `Sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, `Starting materials`, `Reaction type`, `Tags`, `Authors`, `Lab notebook`, `Project`, `Working time`, `Inert atmosphere`, `Created`, `Modified`, `Precursors` and `Sequences`
- **AND** the values include an `a.compound` to `/compounds/acetylsalicylic-acid/` with the text `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `a.compound` links `Salicylic acid` and `Acetic anhydride` under `Starting materials`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `A. Example` and `C. Example`, the texts `AE-1/2`, `Teaching › First-year practical`, `2.5 h` and `No`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, the declared procedure fields' shown labels standing in it, in declared order, between `Checked by` and `Created`; they include every label whose field the content file sets, except `Checked by` where the status is `checked`, with `Product` for one product and `Products` for several, and `Formula`, `MW` and `SMILES` exactly when there is one product, no page has an `ID`, `Scale` or `Yield` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure is linked
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and product name are both `Salicylic acid`, after a theme build
- **THEN** its panel's `Product` pair holds one `a.compound` to `/compounds/salicylic-acid/` with the text `Salicylic acid`

#### Scenario: Panel of a procedure with two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure"
- **THEN** its panel has a `Products` pair with the `a.compound` links `trans-Stilbene` and `cis-Stilbene`, in that order, and no `Product`, `Formula`, `MW`, `CAS` or `SMILES` pair

#### Scenario: Declared fields in the German panel
- **WHEN** a test reads `procedures/osdb-0002/index.html` of a build of the test collection in locale `de`
- **THEN** its panel holds the pairs `Laborjournal` `AE-1/2`, `Projekt` `Lehre › Grundpraktikum`, `Arbeitszeit` `2,5 h` and `Schutzgas` `Nein`, in this order, between the `Autoren` pair and the `Erstellt` pair
