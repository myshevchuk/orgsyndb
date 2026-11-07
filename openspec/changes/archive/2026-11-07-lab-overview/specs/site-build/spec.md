## MODIFIED Requirements

### Requirement: Deployment under a path prefix
A built site SHALL work both at the root of its host and under a path prefix such as `/orgsyndb/`, unchanged, apart from its references to the lab application, which only a build with `params.lab` writes: the header's links to the lab's views and the home page's frame and link (site-theme "Page shell" and "Home page"). The lab serves `/lab/` at its host's root only (container-deployment), so these references work at the root alone. No `href`, `src` or `action` attribute in its HTML begins with `/`. Each that is neither a URI with a scheme, nor a fragment alone, nor a reference to the lab resolves, against the page's URL under any prefix, to a published file under that prefix, its query and fragment aside; each reference to the lab resolves, against the page's URL at the root, to `/lab/` or one of its paths `/lab/summary/`, `/lab/inventory/end-products/`, `/lab/planning/` and `/lab/tasks/`. The catalogue loads the Pagefind bundle relative to its own script URL (site-catalogue "Catalogue script"), so search works under the prefix too.

#### Scenario: Links and assets under a prefix
- **WHEN** a test builds a copy of the test collection, and resolves every `href`, `src` and `action` of every HTML page under `public/` against the page's URL below `http://127.0.0.1/orgsyndb/`
- **THEN** no value begins with `/`, and every value that has no URI scheme and is not a bare fragment resolves to a path under `/orgsyndb/` naming a file, or a directory with an `index.html`, under `public/`

#### Scenario: Search under a prefix
- **WHEN** the orchestrator serves a build's `public/` as the directory `orgsyndb/` of a web root and opens `/orgsyndb/procedures/?q=aspirin` in a browser (manual verification, tasks.md section 6)
- **THEN** the catalogue shows OSDB-0002, its links open procedure pages under `/orgsyndb/`, and the browser fetches nothing outside `/orgsyndb/`

#### Scenario: Lab references at the root
- **WHEN** a test builds a copy of the test collection with `ORGSYNDB_LAB=true`, and resolves every `href`, `src` and `action` of every HTML page under `public/` against the page's URL below `http://127.0.0.1/`
- **THEN** no value begins with `/`, every value that resolves below `/lab/` is `/lab/` or one of the four lab paths, the home page's `iframe` resolves to `/lab/summary/`, and every other value without a URI scheme that is not a bare fragment names a file, or a directory with an `index.html`, under `public/`
