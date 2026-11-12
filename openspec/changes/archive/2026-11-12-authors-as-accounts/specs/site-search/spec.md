## MODIFIED Requirements

### Requirement: Indexed content
The indexed element of a procedure page SHALL be its `article.procedure`, as the site-theme spec places it. The following are outside it, and are never part of the indexed text:
- the sample banner;
- the procedure header (ID line, status badge, `h1`, print facts, actions);
- the site header and its navigation;
- the footer.

The indexed text includes the metadata panel and the index-terms element. The panel shows no ID, and the formula, CAS number and SMILES of a product only when the procedure has one (site-theme "Metadata panel"), so `article.procedure` holds, after the rendered body and before the SMILES index element, a `span.index-terms` carrying `hidden`, whose text is the ID followed, for each product in order, by its shown name, its formula, its CAS number when set and its SMILES, all separated by single spaces. It is never shown, and Pagefind indexes its text. Each of these therefore occurs as a separate word or words in the indexed body:
- the ID;
- every product's name;
- every product's formula;
- every product's CAS number;
- every product's SMILES string;
- every starting material's name;
- each tag;
- the reaction-type label;
- each author's name (procedure-authors "Author data for the site").

#### Scenario: Metadata inside the body, chrome outside
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the text of its single `data-pagefind-body` element contains the ID, every product's shown name, CAS number when set and SMILES, every starting material's shown name, every tag and every author
- **AND** it contains neither the banner text nor the navigation link texts as a sequence
- **AND** it has exactly one `span.index-terms`, carrying `hidden`, whose text is the ID and the product terms as stated

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`
