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

Each account has, whenever the data set is written, the primary key of its row in this table, `1` for `klehmann` to `5` for `mwolf`, so that the Forgejo account linked to it (web-app "Forgejo accounts") stays its own after `--replace`; an account created after the data set takes a key above them. Every account but `mwolf` has the password `demo` and the email address `<user name>@example.org`, so that each can sign in to Forgejo; `mwolf` has none. `mwolf` is named on records made more than a year before `D` and on none made later.

#### Scenario: Signing in
- **WHEN** the data set is written and a test client signs in as `tbauer`, as `klehmann` and as `mwolf`, each with the password `demo`
- **THEN** the first two succeed and `klehmann` reaches `/lab/admin/`, and the third fails

#### Scenario: Email addresses
- **WHEN** the data set is written
- **THEN** `tbauer`'s address is `tbauer@example.org` and `mwolf` has none

#### Scenario: Keys that survive a replace
- **WHEN** the data set is written, a test adds an account `kl`, and `demo_data --replace` runs, and then a test adds an account `tb`
- **THEN** after each write `klehmann` has the primary key 1 and `mwolf` 5, and `tb` has a primary key above 5
