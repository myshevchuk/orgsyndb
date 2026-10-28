## ADDED Requirements

### Requirement: Deployment under a path prefix
A built site SHALL work both at the root of its host and under a path prefix such as `/orgsyndb/`, unchanged. No `href`, `src` or `action` attribute in its HTML begins with `/`; each that is neither a URI with a scheme nor a fragment alone resolves, against the page's URL under any prefix, to a published file under that prefix, its query and fragment aside. The catalogue loads the Pagefind bundle relative to its own script URL (site-catalogue "Catalogue script"), so search works under the prefix too.

#### Scenario: Links and assets under a prefix
- **WHEN** a test builds a copy of the test collection, and resolves every `href`, `src` and `action` of every HTML page under `public/` against the page's URL below `http://127.0.0.1/orgsyndb/`
- **THEN** no value begins with `/`, and every value that has no URI scheme and is not a bare fragment resolves to a path under `/orgsyndb/` naming a file, or a directory with an `index.html`, under `public/`

#### Scenario: Search under a prefix
- **WHEN** the orchestrator serves a build's `public/` as the directory `orgsyndb/` of a web root and opens `/orgsyndb/procedures/?q=aspirin` in a browser (manual verification, tasks.md section 6)
- **THEN** the catalogue shows OSDB-0002, its links open procedure pages under `/orgsyndb/`, and the browser fetches nothing outside `/orgsyndb/`
