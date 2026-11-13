## ADDED Requirements

### Requirement: Checking a manifest
`POST /lab/collection/check/` SHALL take the collection half of a manifest, a JSON object with `language`, `procedures`, `sequences` and `deleted` as `tools/orgsyndb manifest` prints them, with the token, the answers to a missing or wrong token, an empty `ORGSYNDB_BUILDER_TOKEN`, another method and a malformed body of the manifest path (Manifest), and answer `200` with `{"errors": [...]}`: exactly the problems for which an import of it would be refused (Import checks), against the registry and the issued IDs as they are, each a string, in the order the import reports them, and an empty list when there is none. Before the first accepted import, the manifest's IDs and `deleted` count as issued, as the first import adopts them (Issued IDs). It takes no lock, issues no ID, records no import and changes nothing.

#### Scenario: A clean collection
- **WHEN** the builder token is set and a test client posts, with it, the collection half of the demo collection's manifest
- **THEN** the answer is 200 with an empty `errors` and no import exists

#### Scenario: An unissued ID
- **WHEN** after an accepted import the posted collection half holds a procedure `OSDB-0099` the application never issued
- **THEN** the answer is 200, `errors` names `OSDB-0099` as the import would, and no further import exists

#### Scenario: Before the first import
- **WHEN** no import was accepted and the posted collection half holds a procedure `OSDB-0099` the application never issued
- **THEN** `errors` is empty, as the first import would adopt the ID, and no ID was issued

#### Scenario: Without the token
- **WHEN** a test client posts a valid body without a token
- **THEN** the answer is 403 and carries no `errors`
