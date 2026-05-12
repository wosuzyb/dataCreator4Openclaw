# SWEContextBench Lite Repo Materialization Design

## Goal

Materialize the SWEContextBench Lite related tasks as standalone GitHub repositories.
Each unique related task becomes one public repository under `wosuzyb`. The repository
contents are the original upstream project checked out at the benchmark `base_commit`.
Each generated repository receives one issue derived only from the task's
`problem_statement`.

## Inputs

- `SWEContextBench/lite/related.jsonl`
  - Source of the 99 unique related tasks.
  - Provides `instance_id`, `repo`, `base_commit`, and `problem_statement`.
- `SWEContextBench/lite/related_relationship_links.tsv`
  - Source of relationship rows.
  - Used to confirm and enrich local planning, but not appended to created issue bodies.

The workflow deduplicates by `related_instance_id` / `instance_id`. The relationship
TSV has 118 rows, but the target output is 99 repositories.

## Output

For each unique related task:

- Create public GitHub repository `wosuzyb/<related_instance_id>`.
- Push the upstream repository state at that task's `base_commit` to `main`.
- Create exactly one GitHub issue in the new repository.

Issue content rules:

- Title: first line of `problem_statement`.
- Body: full `problem_statement`.
- No appended metadata.

## Version Rule

Use `base_commit` from `SWEContextBench/lite/related.jsonl`.

Do not infer the version from issue creation time. `base_commit` is the benchmark's
intended starting code state for the task, so it is more precise and reproducible.

## Repository Naming

Use the exact related task id as the repository name, for example:

- `astropy__astropy-15082`
- `django__django-30153`

If a repository already exists, the implementation must not blindly overwrite it.
It should detect the existing repository and report the state, or support an explicit
resume mode that verifies whether the existing repository already matches the planned
task.

## Proposed Pipeline

Implement the workflow as a resumable staged pipeline rather than a single opaque
command.

### 1. Prepare Manifest

Read `related.jsonl` and `related_relationship_links.tsv`, deduplicate to 99 tasks,
and write a manifest containing at least:

- `instance_id`
- `repo`
- `base_commit`
- `problem_statement`
- planned GitHub owner: `wosuzyb`
- planned GitHub repo name: `instance_id`

The manifest is the source of truth for later stages.

### 2. Clone And Checkout

Clone upstream repositories locally, reusing one upstream clone per source repository
where practical. For each task, create a separate local working directory whose files
represent the upstream repository checked out at the task's `base_commit`.

The per-task directory should be named after `instance_id`.

### 3. Create GitHub Repositories

Create public repositories under `wosuzyb` using the planned repo names.

This stage requires GitHub credentials with permission to create repositories under
`wosuzyb`.

### 4. Push Code

Push each per-task checkout to the corresponding generated repository's `main`
branch.

The pushed repository should contain the upstream project code at `base_commit`.

### 5. Create Issues

For each generated repository, create one issue:

- Title is the first line of `problem_statement`.
- Body is the complete `problem_statement`.

Do not add original repo, base commit, source URLs, relationship ids, or any other
metadata to the issue body.

### 6. Status And Resume

Record stage status per task so the workflow can be rerun after failures without
duplicating successful work. Expected statuses include:

- manifest prepared
- source checkout prepared
- GitHub repository created or already present
- code pushed
- issue created
- failed with reason

## Error Handling

The implementation should stop or mark a task failed when:

- `base_commit` is missing or does not exist in the upstream repository.
- The target repository already exists and cannot be verified as safe to reuse.
- GitHub authentication lacks access to create repositories under `wosuzyb`.
- Pushing fails.
- Issue creation fails.

Failures should be recorded per task so other independent tasks can continue when
the failure is isolated.

## Safety Controls

The first implementation should support dry-run planning before creating any GitHub
repositories or pushing code.

Dry-run should report:

- number of planned repositories
- target owner and visibility
- repository names
- upstream repositories
- base commits
- issue titles

No public GitHub writes should occur during dry-run.

## Success Criteria

- Exactly 99 unique related tasks are planned.
- Each generated repository is public under `wosuzyb`.
- Each generated repository's `main` branch points to code from the related task's
  upstream `base_commit`.
- Each generated repository has one issue whose title is the first line of
  `problem_statement` and whose body is exactly the full `problem_statement`.
- The process can be resumed without duplicating repositories or issues.
