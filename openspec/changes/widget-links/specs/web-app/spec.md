## ADDED Requirements

### Requirement: Back links
Each of these record pages SHALL begin its `main` content, before its `h1`, with a `p.lab-back` holding one link to the list the record belongs to, whose text is that list's heading, preceded by an arrow `←` hidden from assistive technology:

| Page | Link | Text |
|---|---|---|
| an item, `/lab/inventory/items/<id>/` | `/lab/inventory/end-products/` | `Endprodukte` (`End products`) |
| a batch, `/lab/inventory/batches/<id>/` | `/lab/inventory/batches/` | its list's heading |
| a vessel, `/lab/inventory/vessels/<id>/` | `/lab/inventory/vessels/` | its list's heading |
| a delivery note, `/lab/inventory/deliveries/<id>/` | `/lab/inventory/deliveries/` | its list's heading |
| a task, `/lab/tasks/<number>/` | `/lab/tasks/` | its list's heading |
| a substance, `/lab/registry/substances/<key>/` | `/lab/registry/` | `Substanzen` (`Substances`) |
| a notebook, `/lab/journal/<code>/` | `/lab/journal/` | `Laborjournale` (`Lab notebooks`) |

A list's heading is the `h1` of its page in the same language. The back link is the page's only link to that list outside the navigation and the section tabs.

#### Scenario: Back links match their lists
- **WHEN** the demo data set is written and a test client requests one page of each kind in the table, and each list page the links lead to
- **THEN** each record page has exactly one `p.lab-back`, before its `h1`, whose link leads to the stated list and whose text, without the arrow, equals that list page's `h1`, and the arrow carries `aria-hidden="true"`

#### Scenario: English back links
- **WHEN** a test client with the interface language English requests an item's page and a substance's page
- **THEN** their back links read `End products` and `Substances`
