## ADDED Requirements

### Requirement: Demo site workflow
The repository SHALL ship `.github/workflows/demo-site.yml`, a GitHub Actions workflow that builds the demo collection and publishes it with GitHub Pages:
- **Triggers.** It runs on a push to `main`, on pull requests and on manual dispatch (`workflow_dispatch`).
- **Permissions.** The workflow's default permissions are `contents: read`.
- **Build.** A job named `build` runs in a `fedora:44` container. It installs `emacs-nox`, `git`, `python3` and `hugo` with `dnf`, checks out the repository, runs `tools/orgsyndb -C examples/demo build`, and uploads `examples/demo/public` with `actions/upload-pages-artifact`.
- **Deploy.** A job named `deploy` needs `build` and deploys the artifact with `actions/deploy-pages` to the `github-pages` environment. It runs only when the event is not a pull request and the ref is `refs/heads/main`. It alone is granted `pages: write` and `id-token: write`.

The workflow uses no secrets.

#### Scenario: Workflow is wired
- **WHEN** a test reads `.github/workflows/demo-site.yml` as text
- **THEN** its triggers name `push` with branch `main`, `pull_request` and `workflow_dispatch`, and its top-level permissions are `contents: read`
- **AND** the `build` job names the `fedora:44` container, a `dnf install` of the four packages, the command `tools/orgsyndb -C examples/demo build`, `actions/upload-pages-artifact` and the path `examples/demo/public`
- **AND** the `deploy` job needs `build`, uses `actions/deploy-pages` in the `github-pages` environment, has an `if` condition naming `pull_request` and `refs/heads/main`, and grants `pages: write` and `id-token: write`
- **AND** neither `pages: write` nor `id-token: write` occurs outside the `deploy` job, and the file contains no `secrets.`

#### Scenario: Demo is published
- **WHEN** the orchestrator opens the deployed site after the workflow's first run on `main` (manual verification, tasks.md section 3)
- **THEN** the home page, a procedure page and a browse page load with their styles, and searching `aspirin` on the search page shows OSDB-0002 with a result link that opens its procedure page
