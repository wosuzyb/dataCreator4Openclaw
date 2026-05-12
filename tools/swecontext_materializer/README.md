# SWEContextBench Lite Materializer

This CLI materializes the 99 SWEContextBench Lite related tasks as public GitHub
repositories under `wosuzyb`.

## Requirements

- Python 3
- `git`
- GitHub CLI `gh`
- `gh auth status` must show an account with permission to create public repositories
  under `wosuzyb`.

## Prepare Manifest

```bash
python3 -m tools.swecontext_materializer.cli prepare-manifest
```

Expected output includes:

```text
planned_tasks=99
output=generated/swecontextbench-lite/manifest.jsonl
```

## Dry Run

Run dry-runs before making GitHub writes:

```bash
python3 -m tools.swecontext_materializer.cli clone-checkout --dry-run --limit 2
python3 -m tools.swecontext_materializer.cli create-repos --dry-run --limit 2
python3 -m tools.swecontext_materializer.cli push-repos --dry-run --limit 2
python3 -m tools.swecontext_materializer.cli create-issues --dry-run --limit 2
```

## Real Execution

```bash
python3 -m tools.swecontext_materializer.cli clone-checkout
python3 -m tools.swecontext_materializer.cli create-repos
python3 -m tools.swecontext_materializer.cli push-repos
python3 -m tools.swecontext_materializer.cli create-issues
```

## Status

```bash
python3 -m tools.swecontext_materializer.cli status
```

Status is stored in `generated/swecontextbench-lite/status.json`.

## Active Upstream Repo Workflow

Use `activate-task` when one upstream repo should have one active task repository
at a time.

Example:

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082
```

This will make the active `wosuzyb` fork for `astropy/astropy` look like:

```text
wosuzyb/astropy-15082
```

It will:

- reuse `wosuzyb/astropy-15082` if it already exists
- otherwise rename an existing `wosuzyb` fork of `astropy/astropy`
- otherwise fork `astropy/astropy` and rename the fork
- enable issues
- delete old open issues by default
- close old open PRs and delete their local head branches by default
- delete every branch except `main` by default
- delete every tag by default
- force `main` to the task `base_commit`
- create a new issue from `problem_statement`

GitHub operations that commonly fail transiently during large cleanup runs, such
as tag deletion, are retried automatically for EOF, TLS timeout, and connection
reset errors.

Cleanup controls:

```bash
--cleanup-issues none
--cleanup-issues delete
--cleanup-prs none
--cleanup-prs close
--cleanup-prs close-and-delete-branches
```

Dry-run:

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082 \
  --dry-run
```
