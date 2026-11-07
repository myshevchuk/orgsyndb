## MODIFIED Requirements

### Requirement: Matching tasks and articles
A task SHALL match an item of the inventory `end-products` when the task's product equals the item's article number regardless of case, or when `compound_for` finds a compound for both and it is the same compound. A task matches an article when it matches one of its items. Planning works on articles: all items of the inventory `end-products` with one article number. An item without an article number belongs to no article, matches no task and has no forecast.

#### Scenario: Match by compound and by text
- **WHEN** the index is the demo collection's, items `CH-0012` of 10 µmol and of 50 µmol and an item `NV-7` exist, and tasks name the products `cinnamic-acid` and `nv-7`
- **THEN** the first task matches the article `CH-0012` and both its items, and the second matches `NV-7`

#### Scenario: A position without an article number
- **WHEN** the index is the demo collection's, an item named `1-Phenylethanol` without an article number has 8 containers, and a planned task names the product `1-phenylethanol`
- **THEN** the planning list with `all=1` lists no article for the item, and the task matches no article and shows its entered priority
