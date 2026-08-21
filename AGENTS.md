# Repository Guidance

## Shared Conventions

- Inherit README and Markdown style, GitHub Actions, reusable workflow, pull-request review, workflow failure, commit,
  and release-management rules from `../shared-automation/AGENTS.md`.
- Inherit shared Svelte formatting and source structure from `../svelte-lib/AGENTS.md`; keep existing line breaks when a
  change has no substantive or formatter-driven reason to alter them.

## Rollup Delivery

- Project-specific Rollup inputs include the S3 prefix, bundle file list, and metadata refresh file. The shared workflow
  resolves the latest `svelte-lib` `main` ref to an exact commit SHA during each run.
