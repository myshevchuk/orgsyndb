## MODIFIED Requirements

### Requirement: Accounts and sign-in
The user model SHALL be `accounts.User`, Django's user with a user name of at most 40 letters and digits, single `.`, `-` or `_` allowed between them, as Forgejo takes user names, fixed once the account exists, since procedure files name their authors by it, and with an added `initials`: one to five letters or digits, unique regardless of case, stored in upper case. A user's display name is the full name, or the user name when that is empty. There is no page for creating one's own account; staff create accounts in the admin. A person signs in with user name and password, signs out with a POST, and changes their own password at `/lab/accounts/password/`. An account without a usable password cannot sign in and can still be named on records.

#### Scenario: Initials
- **WHEN** a test creates a user with initials `kl` and then another with `KL`
- **THEN** the first is stored as `KL` and the second fails validation

#### Scenario: Account without a password
- **WHEN** a test creates an account with an unusable password and posts its user name to the sign-in page
- **THEN** sign-in fails, and the account is offered as assignee in the task form

#### Scenario: User names
- **WHEN** a staff user creates accounts in the admin named `a.example`, `a..b`, `-ab`, `ab-` and `Ä.müller`, and then changes the user name of `a.example`
- **THEN** only `a.example` is created, and its user name cannot be changed
