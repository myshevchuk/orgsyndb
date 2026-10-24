# Instructions for coding agents

## Planning

This repo uses OpenSpec

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
