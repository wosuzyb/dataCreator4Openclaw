# SWEContextBench Lite Repo Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable CLI that turns the 99 SWEContextBench Lite related tasks into public GitHub repositories under `wosuzyb`, checked out at each task's `base_commit`, with one issue from `problem_statement`.

**Architecture:** Implement a small Python package under `tools/swecontext_materializer/` with separate modules for data loading, status persistence, git operations, GitHub operations, and CLI orchestration. External writes are gated by explicit CLI stages and `--dry-run`; the manifest is the source of truth for all later stages.

**Tech Stack:** Python 3 standard library, `pytest`, local `git`, GitHub CLI `gh`.

---

## File Structure

- Create `tools/swecontext_materializer/__init__.py`
  - Package marker.
- Create `tools/swecontext_materializer/models.py`
  - Dataclass for `TaskManifest`.
- Create `tools/swecontext_materializer/manifest.py`
  - Read `related.jsonl` and `related_relationship_links.tsv`, deduplicate to 99 tasks, derive issue titles, and write/read manifest JSONL.
- Create `tools/swecontext_materializer/status.py`
  - JSON status file helpers for resumable execution.
- Create `tools/swecontext_materializer/commands.py`
  - Thin subprocess wrapper used by git and GitHub modules.
- Create `tools/swecontext_materializer/git_ops.py`
  - Clone upstream repos once, verify commits, create per-task worktrees/checkouts, and push task repos.
- Create `tools/swecontext_materializer/github_ops.py`
  - Check/create public GitHub repositories and create issues via `gh`.
- Create `tools/swecontext_materializer/cli.py`
  - `prepare-manifest`, `clone-checkout`, `create-repos`, `push-repos`, `create-issues`, and `status` commands.
- Create `tools/swecontext_materializer/README.md`
  - Usage notes and required credentials.
- Create tests under `tests/swecontext_materializer/`.

The implementation should keep all generated runtime output under `generated/swecontextbench-lite/`:

- `manifest.jsonl`
- `status.json`
- `sources/<owner>__<repo>/`
- `tasks/<instance_id>/`

---

### Task 1: Data Models And Manifest Builder

**Files:**
- Create: `tools/swecontext_materializer/__init__.py`
- Create: `tools/swecontext_materializer/models.py`
- Create: `tools/swecontext_materializer/manifest.py`
- Test: `tests/swecontext_materializer/test_manifest.py`

- [ ] **Step 1: Write failing manifest tests**

Create `tests/swecontext_materializer/test_manifest.py`:

```python
import json
from pathlib import Path

from tools.swecontext_materializer.manifest import (
    build_manifest,
    first_problem_statement_line,
    read_manifest_jsonl,
    write_manifest_jsonl,
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_first_problem_statement_line_skips_blank_lines() -> None:
    assert first_problem_statement_line("\n\nBug title\n\nBody") == "Bug title"


def test_build_manifest_deduplicates_relationship_rows(tmp_path: Path) -> None:
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "related_relationship_links.tsv"
    write_jsonl(
        related,
        [
            {
                "instance_id": "astropy__astropy-15082",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "problem_statement": "Title line\n\nFull body",
            }
        ],
    )
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "astropy__astropy-15082\thttps://github.com/astropy/astropy/pull/15082\thttps://github.com/astropy/astropy/issues/15082\texp1\tpr\tissue\n"
        "astropy__astropy-15082\thttps://github.com/astropy/astropy/pull/15082\thttps://github.com/astropy/astropy/issues/15082\texp2\tpr\tissue\n",
        encoding="utf-8",
    )

    manifest = build_manifest(related, relationships, owner="wosuzyb")

    assert len(manifest) == 1
    task = manifest[0]
    assert task.instance_id == "astropy__astropy-15082"
    assert task.target_owner == "wosuzyb"
    assert task.target_repo == "astropy__astropy-15082"
    assert task.issue_title == "Title line"
    assert task.issue_body == "Title line\n\nFull body"
    assert task.related_issue_url == "https://github.com/astropy/astropy/issues/15082"
    assert task.related_pr_url == "https://github.com/astropy/astropy/pull/15082"
    assert task.experience_instance_ids == ["exp1", "exp2"]


def test_manifest_jsonl_round_trip(tmp_path: Path) -> None:
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "related_relationship_links.tsv"
    output = tmp_path / "manifest.jsonl"
    write_jsonl(
        related,
        [
            {
                "instance_id": "django__django-30153",
                "repo": "django/django",
                "base_commit": "def456",
                "problem_statement": "Ticket title\nbody",
            }
        ],
    )
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "django__django-30153\thttps://github.com/django/django/pull/10939\thttps://code.djangoproject.com/ticket/30153\texp3\tpr\tissue\n",
        encoding="utf-8",
    )

    write_manifest_jsonl(build_manifest(related, relationships, "wosuzyb"), output)

    loaded = read_manifest_jsonl(output)
    assert len(loaded) == 1
    assert loaded[0].repo == "django/django"
    assert loaded[0].base_commit == "def456"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_manifest.py -q
```

Expected: FAIL because `tools.swecontext_materializer` does not exist.

- [ ] **Step 3: Implement models and manifest builder**

Create `tools/swecontext_materializer/__init__.py`:

```python
"""SWEContextBench Lite repository materialization tools."""
```

Create `tools/swecontext_materializer/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TaskManifest:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    issue_title: str
    issue_body: str
    target_owner: str
    target_repo: str
    related_pr_url: str | None = None
    related_issue_url: str | None = None
    experience_instance_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskManifest":
        return cls(**data)
```

Create `tools/swecontext_materializer/manifest.py`:

```python
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .models import TaskManifest


def first_problem_statement_line(problem_statement: str) -> str:
    for line in problem_statement.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "SWEContextBench task"


def _read_related_jsonl(path: Path) -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            instance_id = row["instance_id"]
            if instance_id in tasks:
                raise ValueError(f"duplicate instance_id in related JSONL at line {line_number}: {instance_id}")
            tasks[instance_id] = row
    return tasks


def _read_relationships(path: Path) -> dict[str, dict]:
    relationships: dict[str, dict] = defaultdict(
        lambda: {
            "related_pr_url": None,
            "related_issue_url": None,
            "experience_instance_ids": [],
        }
    )
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            instance_id = row["related_instance_id"]
            entry = relationships[instance_id]
            entry["related_pr_url"] = entry["related_pr_url"] or row.get("related_pr_url")
            entry["related_issue_url"] = entry["related_issue_url"] or row.get("related_issue_url")
            experience_id = row.get("experience_instance_id")
            if experience_id and experience_id not in entry["experience_instance_ids"]:
                entry["experience_instance_ids"].append(experience_id)
    return dict(relationships)


def build_manifest(related_jsonl: Path, relationships_tsv: Path, owner: str) -> list[TaskManifest]:
    related_tasks = _read_related_jsonl(related_jsonl)
    relationships = _read_relationships(relationships_tsv)
    manifest: list[TaskManifest] = []

    for instance_id in sorted(related_tasks):
        task = related_tasks[instance_id]
        problem_statement = task["problem_statement"]
        relationship = relationships.get(instance_id, {})
        manifest.append(
            TaskManifest(
                instance_id=instance_id,
                repo=task["repo"],
                base_commit=task["base_commit"],
                problem_statement=problem_statement,
                issue_title=first_problem_statement_line(problem_statement),
                issue_body=problem_statement,
                target_owner=owner,
                target_repo=instance_id,
                related_pr_url=relationship.get("related_pr_url"),
                related_issue_url=relationship.get("related_issue_url"),
                experience_instance_ids=relationship.get("experience_instance_ids", []),
            )
        )

    return manifest


def write_manifest_jsonl(tasks: list[TaskManifest], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for task in tasks:
            handle.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")


def read_manifest_jsonl(path: Path) -> list[TaskManifest]:
    tasks: list[TaskManifest] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tasks.append(TaskManifest.from_dict(json.loads(line)))
    return tasks
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_manifest.py -q
```

Expected: PASS.

---

### Task 2: Status Store And Command Runner

**Files:**
- Create: `tools/swecontext_materializer/status.py`
- Create: `tools/swecontext_materializer/commands.py`
- Test: `tests/swecontext_materializer/test_status_and_commands.py`

- [ ] **Step 1: Write failing tests**

Create `tests/swecontext_materializer/test_status_and_commands.py`:

```python
from pathlib import Path

import pytest

from tools.swecontext_materializer.commands import CommandError, CommandResult, run_command
from tools.swecontext_materializer.status import StatusStore


def test_status_store_records_stage_and_error(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.json")
    store.mark("task-1", "repo_created")
    store.fail("task-2", "push_failed", "permission denied")

    loaded = StatusStore(tmp_path / "status.json")
    assert loaded.stage("task-1") == "repo_created"
    assert loaded.stage("task-2") == "push_failed"
    assert loaded.error("task-2") == "permission denied"


def test_status_store_done_checks_exact_stage(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.json")
    store.mark("task-1", "issue_created")
    assert store.done("task-1", "issue_created")
    assert not store.done("task-1", "code_pushed")


def test_run_command_dry_run_does_not_execute() -> None:
    result = run_command(["definitely-not-a-real-command"], cwd=None, dry_run=True)
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_run_command_raises_on_failure() -> None:
    with pytest.raises(CommandError) as exc:
        run_command(["python3", "-c", "import sys; sys.exit(7)"], cwd=None, dry_run=False)
    assert exc.value.result.returncode == 7
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_status_and_commands.py -q
```

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement status store and command runner**

Create `tools/swecontext_materializer/status.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


class StatusStore:
    def __init__(self, path: Path):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")

    def mark(self, instance_id: str, stage: str) -> None:
        self._data.setdefault(instance_id, {})
        self._data[instance_id]["stage"] = stage
        self._data[instance_id].pop("error", None)
        self._save()

    def fail(self, instance_id: str, stage: str, error: str) -> None:
        self._data.setdefault(instance_id, {})
        self._data[instance_id]["stage"] = stage
        self._data[instance_id]["error"] = error
        self._save()

    def stage(self, instance_id: str) -> str | None:
        return self._data.get(instance_id, {}).get("stage")

    def error(self, instance_id: str) -> str | None:
        return self._data.get(instance_id, {}).get("error")

    def done(self, instance_id: str, stage: str) -> bool:
        return self.stage(instance_id) == stage and self.error(instance_id) is None

    def all(self) -> dict:
        return dict(self._data)
```

Create `tools/swecontext_materializer/commands.py`:

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        super().__init__(f"command failed with exit {result.returncode}: {' '.join(result.args)}")
        self.result = result


def run_command(args: list[str], cwd: Path | None, dry_run: bool = False) -> CommandResult:
    if dry_run:
        return CommandResult(args=args, returncode=0, stdout="", stderr="")
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = CommandResult(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if result.returncode != 0:
        raise CommandError(result)
    return result
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_status_and_commands.py -q
```

Expected: PASS.

---

### Task 3: Git Operations

**Files:**
- Create: `tools/swecontext_materializer/git_ops.py`
- Test: `tests/swecontext_materializer/test_git_ops.py`

- [ ] **Step 1: Write failing git operation tests**

Create `tests/swecontext_materializer/test_git_ops.py`:

```python
from pathlib import Path

from tools.swecontext_materializer.git_ops import (
    source_clone_dir,
    task_checkout_dir,
    upstream_url,
)
from tools.swecontext_materializer.models import TaskManifest


def task() -> TaskManifest:
    return TaskManifest(
        instance_id="astropy__astropy-15082",
        repo="astropy/astropy",
        base_commit="abc123",
        problem_statement="Title\nBody",
        issue_title="Title",
        issue_body="Title\nBody",
        target_owner="wosuzyb",
        target_repo="astropy__astropy-15082",
    )


def test_upstream_url() -> None:
    assert upstream_url("astropy/astropy") == "https://github.com/astropy/astropy.git"


def test_source_clone_dir_replaces_slash(tmp_path: Path) -> None:
    assert source_clone_dir(tmp_path, "astropy/astropy") == tmp_path / "sources" / "astropy__astropy"


def test_task_checkout_dir_uses_instance_id(tmp_path: Path) -> None:
    assert task_checkout_dir(tmp_path, task()) == tmp_path / "tasks" / "astropy__astropy-15082"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_git_ops.py -q
```

Expected: FAIL because `git_ops.py` does not exist.

- [ ] **Step 3: Implement git operations**

Create `tools/swecontext_materializer/git_ops.py`:

```python
from __future__ import annotations

import shutil
from pathlib import Path

from .commands import run_command
from .models import TaskManifest


def upstream_url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def source_clone_dir(workdir: Path, repo: str) -> Path:
    return workdir / "sources" / repo.replace("/", "__")


def task_checkout_dir(workdir: Path, task: TaskManifest) -> Path:
    return workdir / "tasks" / task.instance_id


def ensure_source_clone(workdir: Path, repo: str, dry_run: bool = False) -> Path:
    clone_dir = source_clone_dir(workdir, repo)
    clone_dir.parent.mkdir(parents=True, exist_ok=True)
    if clone_dir.exists():
        run_command(["git", "fetch", "--all", "--tags"], cwd=clone_dir, dry_run=dry_run)
    else:
        run_command(["git", "clone", upstream_url(repo), str(clone_dir)], cwd=None, dry_run=dry_run)
    return clone_dir


def verify_commit_exists(source_dir: Path, base_commit: str, dry_run: bool = False) -> None:
    run_command(["git", "rev-parse", "--verify", f"{base_commit}^{{commit}}"], cwd=source_dir, dry_run=dry_run)


def prepare_task_checkout(workdir: Path, task: TaskManifest, dry_run: bool = False) -> Path:
    source_dir = ensure_source_clone(workdir, task.repo, dry_run=dry_run)
    verify_commit_exists(source_dir, task.base_commit, dry_run=dry_run)
    checkout_dir = task_checkout_dir(workdir, task)
    if checkout_dir.exists() and not dry_run:
        shutil.rmtree(checkout_dir)
    checkout_dir.parent.mkdir(parents=True, exist_ok=True)
    run_command(["git", "clone", str(source_dir), str(checkout_dir)], cwd=None, dry_run=dry_run)
    run_command(["git", "checkout", "-B", "main", task.base_commit], cwd=checkout_dir, dry_run=dry_run)
    return checkout_dir


def push_task_checkout(workdir: Path, task: TaskManifest, dry_run: bool = False) -> None:
    checkout_dir = task_checkout_dir(workdir, task)
    target_url = f"https://github.com/{task.target_owner}/{task.target_repo}.git"
    run_command(["git", "remote", "remove", "origin"], cwd=checkout_dir, dry_run=dry_run)
    run_command(["git", "remote", "add", "origin", target_url], cwd=checkout_dir, dry_run=dry_run)
    run_command(["git", "push", "--force", "-u", "origin", "main"], cwd=checkout_dir, dry_run=dry_run)
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_git_ops.py -q
```

Expected: PASS.

---

### Task 4: GitHub Operations

**Files:**
- Create: `tools/swecontext_materializer/github_ops.py`
- Test: `tests/swecontext_materializer/test_github_ops.py`

- [ ] **Step 1: Write failing GitHub command tests**

Create `tests/swecontext_materializer/test_github_ops.py`:

```python
from tools.swecontext_materializer.github_ops import create_issue_args, create_repo_args, repo_view_args
from tools.swecontext_materializer.models import TaskManifest


def task() -> TaskManifest:
    return TaskManifest(
        instance_id="astropy__astropy-15082",
        repo="astropy/astropy",
        base_commit="abc123",
        problem_statement="Title\nBody",
        issue_title="Title",
        issue_body="Title\nBody",
        target_owner="wosuzyb",
        target_repo="astropy__astropy-15082",
    )


def test_create_repo_args_public_under_owner() -> None:
    assert create_repo_args(task()) == [
        "gh",
        "repo",
        "create",
        "wosuzyb/astropy__astropy-15082",
        "--public",
        "--confirm",
    ]


def test_repo_view_args() -> None:
    assert repo_view_args(task()) == ["gh", "repo", "view", "wosuzyb/astropy__astropy-15082"]


def test_create_issue_args_uses_title_and_body_only() -> None:
    assert create_issue_args(task()) == [
        "gh",
        "issue",
        "create",
        "--repo",
        "wosuzyb/astropy__astropy-15082",
        "--title",
        "Title",
        "--body",
        "Title\nBody",
    ]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_github_ops.py -q
```

Expected: FAIL because `github_ops.py` does not exist.

- [ ] **Step 3: Implement GitHub operations**

Create `tools/swecontext_materializer/github_ops.py`:

```python
from __future__ import annotations

from .commands import CommandError, run_command
from .models import TaskManifest


def full_repo_name(task: TaskManifest) -> str:
    return f"{task.target_owner}/{task.target_repo}"


def repo_view_args(task: TaskManifest) -> list[str]:
    return ["gh", "repo", "view", full_repo_name(task)]


def create_repo_args(task: TaskManifest) -> list[str]:
    return ["gh", "repo", "create", full_repo_name(task), "--public", "--confirm"]


def create_issue_args(task: TaskManifest) -> list[str]:
    return [
        "gh",
        "issue",
        "create",
        "--repo",
        full_repo_name(task),
        "--title",
        task.issue_title,
        "--body",
        task.issue_body,
    ]


def repo_exists(task: TaskManifest, dry_run: bool = False) -> bool:
    try:
        run_command(repo_view_args(task), cwd=None, dry_run=dry_run)
        return True
    except CommandError:
        return False


def create_repo(task: TaskManifest, dry_run: bool = False) -> str:
    if repo_exists(task, dry_run=dry_run):
        return "already_present"
    run_command(create_repo_args(task), cwd=None, dry_run=dry_run)
    return "created"


def create_issue(task: TaskManifest, dry_run: bool = False) -> None:
    run_command(create_issue_args(task), cwd=None, dry_run=dry_run)
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_github_ops.py -q
```

Expected: PASS.

---

### Task 5: CLI Orchestration

**Files:**
- Create: `tools/swecontext_materializer/cli.py`
- Test: `tests/swecontext_materializer/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/swecontext_materializer/test_cli.py`:

```python
import json
from pathlib import Path

from tools.swecontext_materializer.cli import main


def test_prepare_manifest_command_writes_manifest(tmp_path: Path) -> None:
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "relationships.tsv"
    output = tmp_path / "manifest.jsonl"
    related.write_text(
        json.dumps(
            {
                "instance_id": "astropy__astropy-15082",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "problem_statement": "Title\nBody",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "prepare-manifest",
            "--related-jsonl",
            str(related),
            "--relationships-tsv",
            str(relationships),
            "--owner",
            "wosuzyb",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["target_owner"] == "wosuzyb"


def test_status_command_prints_status(tmp_path: Path, capsys) -> None:
    status = tmp_path / "status.json"
    status.write_text('{"task-1": {"stage": "issue_created"}}', encoding="utf-8")

    exit_code = main(["status", "--status-file", str(status)])

    assert exit_code == 0
    assert "task-1" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_cli.py -q
```

Expected: FAIL because `cli.py` does not exist.

- [ ] **Step 3: Implement CLI**

Create `tools/swecontext_materializer/cli.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .git_ops import prepare_task_checkout, push_task_checkout
from .github_ops import create_issue, create_repo
from .manifest import build_manifest, read_manifest_jsonl, write_manifest_jsonl
from .status import StatusStore


DEFAULT_WORKDIR = Path("generated/swecontextbench-lite")
DEFAULT_MANIFEST = DEFAULT_WORKDIR / "manifest.jsonl"
DEFAULT_STATUS = DEFAULT_WORKDIR / "status.json"


def add_common_execution_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)


def selected_tasks(manifest_path: Path, limit: int | None):
    tasks = read_manifest_jsonl(manifest_path)
    return tasks if limit is None else tasks[:limit]


def cmd_prepare_manifest(args: argparse.Namespace) -> int:
    tasks = build_manifest(args.related_jsonl, args.relationships_tsv, args.owner)
    write_manifest_jsonl(tasks, args.output)
    print(f"planned_tasks={len(tasks)}")
    print(f"output={args.output}")
    return 0


def cmd_clone_checkout(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            prepare_task_checkout(args.workdir, task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "source_checkout_prepared")
            print(f"{task.instance_id}: source_checkout_prepared")
        except Exception as exc:
            status.fail(task.instance_id, "source_checkout_failed", str(exc))
            print(f"{task.instance_id}: source_checkout_failed: {exc}")
    return 0


def cmd_create_repos(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            result = create_repo(task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "repo_created")
            print(f"{task.instance_id}: repo_{result}")
        except Exception as exc:
            status.fail(task.instance_id, "repo_create_failed", str(exc))
            print(f"{task.instance_id}: repo_create_failed: {exc}")
    return 0


def cmd_push_repos(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            push_task_checkout(args.workdir, task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "code_pushed")
            print(f"{task.instance_id}: code_pushed")
        except Exception as exc:
            status.fail(task.instance_id, "push_failed", str(exc))
            print(f"{task.instance_id}: push_failed: {exc}")
    return 0


def cmd_create_issues(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            create_issue(task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "issue_created")
            print(f"{task.instance_id}: issue_created")
        except Exception as exc:
            status.fail(task.instance_id, "issue_create_failed", str(exc))
            print(f"{task.instance_id}: issue_create_failed: {exc}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    print(json.dumps(status.all(), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swecontext-materializer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-manifest")
    prepare.add_argument("--related-jsonl", type=Path, default=Path("SWEContextBench/lite/related.jsonl"))
    prepare.add_argument("--relationships-tsv", type=Path, default=Path("SWEContextBench/lite/related_relationship_links.tsv"))
    prepare.add_argument("--owner", default="wosuzyb")
    prepare.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)
    prepare.set_defaults(func=cmd_prepare_manifest)

    for name, func in [
        ("clone-checkout", cmd_clone_checkout),
        ("create-repos", cmd_create_repos),
        ("push-repos", cmd_push_repos),
        ("create-issues", cmd_create_issues),
    ]:
        command = subparsers.add_parser(name)
        add_common_execution_args(command)
        command.set_defaults(func=func)

    status = subparsers.add_parser("status")
    status.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_cli.py -q
```

Expected: PASS.

---

### Task 6: Documentation And End-To-End Dry Run

**Files:**
- Create: `tools/swecontext_materializer/README.md`

- [ ] **Step 1: Write usage documentation**

Create `tools/swecontext_materializer/README.md`:

```markdown
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
```

- [ ] **Step 2: Run all unit tests**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer -q
```

Expected: PASS.

- [ ] **Step 3: Prepare real manifest from downloaded data**

Run:

```bash
python3 -m tools.swecontext_materializer.cli prepare-manifest
```

Expected output:

```text
planned_tasks=99
output=generated/swecontextbench-lite/manifest.jsonl
```

- [ ] **Step 4: Verify manifest task count**

Run:

```bash
wc -l generated/swecontextbench-lite/manifest.jsonl
```

Expected output begins with:

```text
99 generated/swecontextbench-lite/manifest.jsonl
```

- [ ] **Step 5: Dry-run the first two tasks through every stage**

Run:

```bash
python3 -m tools.swecontext_materializer.cli clone-checkout --dry-run --limit 2
python3 -m tools.swecontext_materializer.cli create-repos --dry-run --limit 2
python3 -m tools.swecontext_materializer.cli push-repos --dry-run --limit 2
python3 -m tools.swecontext_materializer.cli create-issues --dry-run --limit 2
```

Expected: each command exits 0 and prints two task lines. No GitHub repositories or
issues are created because `--dry-run` is set.

---

### Task 7: Controlled Real Run Procedure

**Files:**
- No code changes.
- Runtime output: `generated/swecontextbench-lite/`

- [ ] **Step 1: Verify GitHub authentication**

Run:

```bash
gh auth status
```

Expected: authenticated account can create public repositories under `wosuzyb`.

- [ ] **Step 2: Run a one-task real smoke test**

Run:

```bash
python3 -m tools.swecontext_materializer.cli clone-checkout --limit 1
python3 -m tools.swecontext_materializer.cli create-repos --limit 1
python3 -m tools.swecontext_materializer.cli push-repos --limit 1
python3 -m tools.swecontext_materializer.cli create-issues --limit 1
python3 -m tools.swecontext_materializer.cli status
```

Expected:

- one public repo is created under `wosuzyb`
- repo `main` contains the upstream checkout at `base_commit`
- one issue exists
- issue title is the first line of `problem_statement`
- issue body is exactly the full `problem_statement`

- [ ] **Step 3: Inspect the smoke-test repository manually**

Open the created GitHub repository page and inspect:

- repository visibility is public
- pushed files match the source project
- issue body has no appended metadata

- [ ] **Step 4: Run remaining tasks**

Run:

```bash
python3 -m tools.swecontext_materializer.cli clone-checkout
python3 -m tools.swecontext_materializer.cli create-repos
python3 -m tools.swecontext_materializer.cli push-repos
python3 -m tools.swecontext_materializer.cli create-issues
```

Expected: all 99 tasks eventually reach `issue_created` in the status file.

- [ ] **Step 5: Verify final status**

Run:

```bash
python3 -m tools.swecontext_materializer.cli status
```

Expected: every task has stage `issue_created` and no `error` field.

---

## Self-Review Notes

- Spec coverage:
  - 99 unique related tasks: Task 1 and Task 6.
  - `base_commit` version rule: Task 1 manifest and Task 3 checkout.
  - public repos under `wosuzyb`: Task 4 and Task 5.
  - issue title/body from `problem_statement` only: Task 1 and Task 4.
  - dry-run and resume/status: Task 2, Task 5, Task 6, Task 7.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: `TaskManifest` fields match all module and test usage.
