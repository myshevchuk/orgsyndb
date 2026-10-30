## MODIFIED Requirements

### Requirement: Fixed scope on term pages
A term page's catalogue SHALL treat its term as a fixed scope, applied with every user choice:
- **Static label.** `p.catalogue-scope` reads `Only procedures of the reaction type <label>`, `Only procedures with the tag <tag>` or `Only procedures by <author>`, then ` · ` and an `a` with `data-browse-all`, the text `Browse all procedures` and the `href` `/procedures/`. It holds no other link.
- **Fixed facet.** The page's facet is a `details.facet` carrying `data-fixed` and `open`, whose only value is the term, its checkbox `checked` and `disabled`. The other three facets list their values as on `/procedures/`; a value that no row of the page carries counts 0, so the script shows it only while it is selected.
- **Results.** The records are the page's rows, so no search result or filter shows a procedure outside the scope; `Clear all` keeps the scope.
- **Browse all.** The script sets the `data-browse-all` link to its original URL followed by `serialize` of the current state, which never holds a value of the fixed facet. Without JavaScript it leads to `/procedures/`.

#### Scenario: Scope in the HTML
- **WHEN** a test scans `public/tags/cinnamate/index.html`, `public/reaction_types/hydrolysis/index.html` and `public/authors/a.-example/index.html` after a theme build in locale `en`
- **THEN** each has the scope text and the `Browse all procedures` link to `/procedures/` as the scope line's only link, and the fixed facet with one checked, disabled value, while its other facets list the same values as those of `/procedures/`

#### Scenario: Searching inside a scope
- **WHEN** the orchestrator opens `/tags/cinnamate/?author=a.+example`, then `/tags/cinnamate/`, chooses a sort, searches `acid`, ticks a status, follows Browse all procedures, goes Back and presses Clear all (manual verification, tasks.md section 6)
- **THEN** the first shows no row and the author as a removable selection with the count 0; every row shown on the term page carries the tag `cinnamate`; the link leads to `/procedures/` with the query, the status and the sort and without the tag; and Clear all keeps the scope and the sort
