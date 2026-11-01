## MODIFIED Requirements

### Requirement: Scope table on the page
A general procedure's page SHALL hold, inside `article.procedure` after the details wrapper and before the rendered body, a `section.scope` with the `h2` `Scope` and a `table.scope-table`. Its header cells are `Entry`, `Starting materials`, `Products` and `Yield`, then `Scale`, `Time`, `Temperature` and `Note`, each of the last four only when some entry sets its key. Each entry gives one body row, in order, whose cells hold:
- the entry's number;
- one `a.compound` per substrate, linking its compound page with the compound's shown name, each followed by its note of compound-fields "Values beside compound links" when it has one, joined by `, `;
- per product, when its compound sets `structure_image`, an `img.scope-structure` with `alt` `Structure of <name>`, `loading="lazy"` and `decoding="async"`, then an `a.compound` linking its compound page with its shown name, followed by its note as for a substrate; the products separated by `, `;
- the yields as `<n> %`, in product order, joined by `, `;
- the scale, the time, the temperature as `<t> °C` and the note, as set, an unset key giving an empty cell.

Numbers are written with the site language's decimal separator. A specific procedure's page has no `section.scope`.

#### Scenario: Scope table of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure after a theme build in locale `en`
- **THEN** its `section.scope` lies between the details wrapper and the `Summary` heading, its header cells are those its entries' keys call for, in order, and its rows give each entry's compounds, links, yields and deviations as stated

#### Scenario: No scope table on a specific procedure
- **WHEN** a test scans every other procedure page of the same build
- **THEN** none has a `section.scope`
