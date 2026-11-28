## MODIFIED Requirements

### Requirement: Back links
Each of these record pages SHALL begin its own content with a `p.lab-back`, after the notices of the page shell (the demo note and the messages, Page shell) and before its `h1`, holding one link to the list the record belongs to, with the record selected, whose text is that list's heading, preceded by an arrow `←` hidden from assistive technology:

| Page | Link | Text |
|---|---|---|
| an item, `/lab/inventory/items/<id>/` | `/lab/inventory/end-products/?selected=<id>` | `Endprodukte` (`End products`) |
| a batch, `/lab/inventory/batches/<id>/` | `/lab/inventory/batches/?selected=<id>` | its list's heading |
| a vessel, `/lab/inventory/vessels/<id>/` | `/lab/inventory/vessels/?selected=<id>` | its list's heading |
| a delivery note, `/lab/inventory/deliveries/<id>/` | `/lab/inventory/deliveries/?selected=<id>` | its list's heading |
| a task, `/lab/tasks/<number>/` | `/lab/tasks/?selected=<number>` | its list's heading |
| a substance, `/lab/registry/substances/<key>/` | `/lab/registry/?selected=<key>` | `Substanzen` (`Substances`) |
| a notebook, `/lab/journal/<code>/` | `/lab/journal/` | `Laborjournale` (`Lab notebooks`) |

A list's heading is the `h1` of its page in the same language. A task the task list hides by default, one neither planned, running nor needing follow-up, adds `state=all` before `selected`, and a used-up vessel adds `empty=1`, so the list shows the record it selects. The notebook list selects nothing, so its link carries no `selected`. When the page was opened from a page of that list in the same tab, activating the link with no modifier key returns there as the browser's back button does, so the list shows the filters, selection and view it had; otherwise, and without scripts, the link opens its address.

The back link is the page's only link to that list outside the navigation and the section tabs; the notebook page's former plain link to `/lab/journal/` is gone.

#### Scenario: Back links match their lists
- **WHEN** the demo data set is written and a test client requests one page of each kind in the table, and each list page the links lead to
- **THEN** each record page has exactly one `p.lab-back`, after the demo note and before its `h1`, whose link leads to the stated address and whose text, without the arrow, equals that list page's `h1`, and the arrow carries `aria-hidden="true"`
- **AND** outside the navigation and the section tabs, each record page has exactly one link to its list, the back link
- **AND** each list page selects the record its back link names

#### Scenario: Back to the list as it was
- **WHEN** a user on `/lab/registry/?q=aceto&selected=acetophenone` opens the substance's page from the details and activates its back link
- **THEN** the browser goes back one step to `/lab/registry/?q=aceto&selected=acetophenone`, as its back button would, and requests no other address
- **AND** on the same page opened directly in a new tab, the back link opens `/lab/registry/?selected=acetophenone`

#### Scenario: English back links
- **WHEN** a test client with the interface language English requests one page of each kind in the table, and each list page
- **THEN** each back link's text, without the arrow, equals the English list page's `h1`, `End products` and `Substances` among them
