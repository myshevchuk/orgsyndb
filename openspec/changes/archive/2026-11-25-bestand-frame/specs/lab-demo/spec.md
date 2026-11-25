## MODIFIED Requirements

### Requirement: Demo database
A database SHALL be a demo database when it holds the demo mark, which the demo data set writes with the day `D` it was seeded as of. On a demo database, every page of the application but the admin's shows once a `p` with the class `lab-demo` and the text `Demo: Alle Einträge sind erfunden (Stand: <D>).` (`Demo: All records are invented (as of <D>).`), `<D>` in the date format of the interface language. Its sign-in page shows, below the form, an element with the class `lab-demo-accounts` listing the user names of the demo accounts that can sign in (Demo accounts), each with its display name, and the text `Passwort für alle: demo` (`Password for all: demo`). A database without the mark shows neither, whatever `ORGSYNDB_DEMO` says.

#### Scenario: Banner
- **WHEN** the data set is written as of 2026-11-07 and a test client requests `/lab/tasks/`, `/lab/planning/`, `/lab/inventory/end-products/` and `/lab/admin/login/`
- **THEN** the first three show `Demo: Alle Einträge sind erfunden (Stand: 07.11.2026).` once, and the admin's page does not

#### Scenario: Sign-in note
- **WHEN** the data set is written and a test client requests `/lab/accounts/login/`
- **THEN** below the form it lists `klehmann`, `tbauer`, `aschmidt` and `jkoch` with their display names and the text `Passwort für alle: demo`, and does not list `mwolf`

#### Scenario: Not a demo database
- **WHEN** `ORGSYNDB_DEMO` is true, the database holds an account and a task but no demo mark, and a test client requests `/lab/tasks/` and `/lab/accounts/login/`
- **THEN** neither page has an element with the class `lab-demo` or `lab-demo-accounts`
