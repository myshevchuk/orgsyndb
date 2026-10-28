## MODIFIED Requirements

### Requirement: Indexed content
The indexed element of a procedure page SHALL be its `article.procedure`, as the site-theme spec places it. The following are outside it, and are never part of the indexed text:
- the sample banner;
- the procedure header (ID line, status badge, `h1`, print facts, actions);
- the site header and its navigation;
- the footer.

The indexed text includes the metadata panel and the index-terms element. The panel shows neither the ID nor a product name that equals the title (site-theme "Metadata panel"), so `article.procedure` holds, after the rendered body and before the SMILES index element, a `span.index-terms` carrying `hidden`, whose text is the ID, a space and `product.name`, or the ID alone when the product has no name. It is never shown, and Pagefind indexes its text. Each of these therefore occurs as a separate word or words in the indexed body:
- the ID;
- the product name;
- the formula;
- the CAS number;
- the SMILES string;
- each tag;
- the reaction-type label;
- each author.

#### Scenario: Metadata inside the body, chrome outside
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the text of its single `data-pagefind-body` element contains the ID, `product.name`, `product.cas` when set, `product.smiles`, every tag and every author
- **AND** it contains neither the banner text nor the navigation link texts as a sequence
- **AND** it has exactly one `span.index-terms`, carrying `hidden`, whose text is the ID and `product.name` separated by a space

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`
