## MODIFIED Requirements

### Requirement: Import checks
Before applying a built manifest, the application SHALL check it against its registry and its own content, and refuse it with one error for each of these, each beginning with the ID it concerns:

- an ID that occurs twice among the procedures or among the sequences: `<ID>: named twice`;
- after the first accepted import, an ID the application has not issued (Issued IDs): `<ID>: not issued by the lab application`;
- a procedure's reaction type that the registry lacks: `<ID>: unknown reaction type "<key>"`;
- a procedure's `notebook` that is not `<code>/<number>`: `<ID>: notebook "<value>" is not <code>/<number>`; one whose code no notebook of the application has: `<ID>: unknown notebook "<code>"`; and one that another procedure of the manifest names too: `<ID>: notebook entry <entry> is also named by <other ID>`;
- a procedure's project that the registry lacks: `<ID>: unknown project "<key>"`;
- an author whose user name no account has: `<ID>: unknown author "<name>"`;
- a substance key in an entry that the registry lacks: `<ID>: unknown substance "<key>"`;
- two entries of one procedure with the same signature: `<ID>: entries <n> and <m> have the signature <signature>`;
- a procedure with no entry: `<ID>: no entry`;
- a sequence target that the registry lacks: `<ID>: unknown target "<key>"`;
- a step naming a procedure the manifest does not hold: `<ID>: step <n> names <procedure>, which is not in the collection`;
- a step of a general procedure that gives no entry number or one that does not count one of its entries from 1, or a step of a specific procedure that gives one: `<ID>: step <n> names no entry of <procedure>`.

A refused import writes no procedure, entry or sequence.

#### Scenario: Unknown substance
- **WHEN** a test posts the demo manifest after replacing a product of `OSDB-0002` with `no-such-substance`
- **THEN** the import is refused with an error `OSDB-0002: unknown substance "no-such-substance"`, and no procedure exists

#### Scenario: One signature twice
- **WHEN** a test posts a manifest whose general procedure `OSDB-0009` has entries 1 and 3 with the same substrates and products
- **THEN** the import is refused with an error beginning `OSDB-0009: entries 1 and 3 have the signature`

#### Scenario: A step beyond the entries
- **WHEN** a test posts the demo manifest after setting the entry of the second step of `SEQ-0002` to 9
- **THEN** the import is refused with the error `SEQ-0002: step 2 names no entry of OSDB-0009`

#### Scenario: Unknown author
- **WHEN** a test posts the demo manifest after setting the authors of `OSDB-0002` to `["nobody"]`
- **THEN** the import is refused with an error `OSDB-0002: unknown author "nobody"`

#### Scenario: An ID not issued
- **WHEN** the demo collection was imported and a test posts its manifest with an added procedure `OSDB-0990` that nobody took
- **THEN** the import is refused with the error `OSDB-0990: not issued by the lab application`, and after user `klehmann` takes `OSDB-0990` the manifest, posted again as a new build, is accepted

#### Scenario: An unknown notebook
- **WHEN** a test posts the demo manifest after setting the `notebook` of `OSDB-0002` to `ZZ-9/1`
- **THEN** the import is refused with an error `OSDB-0002: unknown notebook "ZZ-9"`

#### Scenario: One entry, two procedures
- **WHEN** a test posts the demo manifest after setting the `notebook` of `OSDB-0003` to `AE-1/2`
- **THEN** the import is refused with the errors `OSDB-0002: notebook entry AE-1/2 is also named by OSDB-0003` and `OSDB-0003: notebook entry AE-1/2 is also named by OSDB-0002`

### Requirement: Issued IDs
The application SHALL issue the IDs of procedures, `OSDB-NNNN`, and of sequences, `SEQ-NNNN`, and keep each issued ID once, with the account it was issued to, none for an adopted one, and when it was issued (Imported rows). Issuing and adopting take the lock (One lock).

- `POST /lab/collection/ids/` with a body `{"kind": "procedure"}` or `{"kind": "sequence"}` and an access token (web-app "Access tokens") issues to the token's account the ID of that kind one above the highest issued one, and answers 201 with `{"id": <ID>}`. A request without a valid token answers 401, whether or not it carries a signed-in session; a body of another shape 400; a request made before the application has accepted an import, or for a kind whose ID `9999` is issued, 409 with `{"error": <message>}`. None of them issues anything. The path is exempt from CSRF checks, never redirects and answers JSON.
- The first import the application accepts adopts every ID that its manifest names under `procedures`, `sequences` and `deleted` (Manifest) and that is not issued. A refused import adopts nothing. Later imports adopt nothing and ignore `deleted`; they refuse an ID that is not issued (Import checks).
- `manage.py adopt_ids ID...` adopts each named ID that is not issued, printing `adopted <ID>`, prints `<ID> was issued` for one that was, and exits 0. It exits 1, adopting nothing, with a message naming the first argument that is not a procedure or sequence ID, and is a usage error without arguments.
- The admin lists issued IDs for staff, read-only.

#### Scenario: Two IDs in turn
- **WHEN** the demo data set is written and user `klehmann` requests a procedure ID with a token, and then user `tbauer` does
- **THEN** the answers are the two procedure IDs after the highest the demo collection names, such as `OSDB-0031` and `OSDB-0032` after `OSDB-0030`, the first issued to `klehmann` and the second to `tbauer`

#### Scenario: A sequence ID
- **WHEN** the demo data set is written and a client requests a sequence ID with a token
- **THEN** the answer is the sequence ID after the highest the demo collection names

#### Scenario: Not before an import
- **WHEN** the demo registry is loaded, no import exists, and user `klehmann` requests a procedure ID with a token
- **THEN** the answer is 409 and no ID is issued

#### Scenario: A session is not a token
- **WHEN** the demo data set is written and a client signed in as `klehmann` posts `{"kind": "procedure"}` to `/lab/collection/ids/` without a token
- **THEN** the answer is 401 and no ID is issued to `klehmann`

#### Scenario: Adopted by the first accepted import
- **WHEN** the demo registry is loaded, no import exists, a manifest that names an unknown substance is refused, and then the demo collection's manifest with `deleted` set to `["OSDB-0990"]` is accepted
- **THEN** the IDs of the demo's procedures and sequences and `OSDB-0990` are issued, to no account, and the next procedure ID issued is `OSDB-0991`

#### Scenario: Adopting by hand
- **WHEN** the demo data set is written and an operator runs `manage.py adopt_ids OSDB-0990 OSDB-0003`, and then a test posts the demo manifest with an added procedure `OSDB-0990`
- **THEN** the command prints `adopted OSDB-0990` and `OSDB-0003 was issued`, and the import is accepted
- **AND** `manage.py adopt_ids OSDB-12` exits 1 and adopts nothing
