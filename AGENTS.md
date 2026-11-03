# Instructions for coding agents

## Planning

This repo uses OpenSpec

## Branches

- `develop` is the working branch. Commit work that needs no proposal
  on `develop`. A change's branch starts from `develop`; archive the
  change on its branch, then squash-merge it into `develop`.
- `main` is stable, and every push to it deploys the demo site. Move
  it only when the owner asks, and only by fast-forward to a commit of
  `develop`. Never commit on `main` or squash into it.
- GitHub's default branch is `main`, so open pull requests with
  `--base develop`.
- Both branches reject force-pushes, deletion, merge commits and
  unsigned commits.

## Committing

This repo uses Conventional Commits

Commit subjects should be at most 50 characters long, wrap commit bodies at 72 characters

## AI attribution

Use a custom commit trailer of the form:

Model: model-generation

## Specs and documentation

Specs say what the software does and when, not how it came to be.
Record rationale or history only when the software cannot be
understood or work correctly without it.

- Do not keep transient material in the repository: design drafts,
  mock-ups, decision logs or notes to yourself. Create such files only
  when the owner asks for them.
- When a file or directory is deleted, remove the references to it from
  the living specs (`openspec/specs/`) and documentation. Archived
  changes under `openspec/changes/archive/` record what was true when
  they were made; leave them as they are.
- The product is an early alpha with no users. Do not add backward
  compatibility, migration guides or deprecation paths.
