## MODIFIED Requirements

### Requirement: Demo accounts
The data set SHALL hold five accounts:

| User name  | Name           | Initials | Account                    |
|------------|----------------|----------|----------------------------|
| `klehmann` | Katrin Lehmann | `KL`     | superuser and staff        |
| `tbauer`   | Tobias Bauer   | `TB`     |                            |
| `aschmidt` | Anna Schmidt   | `AS`     |                            |
| `jkoch`    | Jonas Koch     | `JK`     |                            |
| `mwolf`    | Miriam Wolf    | `MW`     | without a usable password  |

Every account but `mwolf` has the password `demo` and the email address `<user name>@example.org`, so that each can sign in to Forgejo; `mwolf` has none. `mwolf` is named on records made more than a year before `D` and on none made later.

#### Scenario: Signing in
- **WHEN** the data set is written and a test client signs in as `tbauer`, as `klehmann` and as `mwolf`, each with the password `demo`
- **THEN** the first two succeed and `klehmann` reaches `/lab/admin/`, and the third fails

#### Scenario: Email addresses
- **WHEN** the data set is written
- **THEN** `tbauer`'s address is `tbauer@example.org` and `mwolf` has none
