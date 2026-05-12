# SWEContextBench Active Upstream Repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `activate-task` CLI command that reuses one active fork per upstream repo, renames it to `<repo-name>-<task-number>`, moves `main` to the task `base_commit`, cleans old issues/PRs by policy, and creates the current task issue.

**Architecture:** Keep manifest parsing as the source of task truth. Add focused helpers for target repo naming, GitHub repo discovery/rename/fork/ref updates, cleanup operations, and activation orchestration; keep `cli.py` as argument parsing and status reporting only.

**Tech Stack:** Python 3 standard library, `pytest`, GitHub CLI `gh`, local `git` only for read-only verification and fallback checks.

---

## File Structure

- Modify `tools/swecontext_materializer/models.py`
  - Add `ActivationResult` dataclass.
- Create `tools/swecontext_materializer/naming.py`
  - Convert `instance_id` and `repo` into active target repo names such as `astropy-15082`.
- Extend `tools/swecontext_materializer/github_ops.py`
  - Add command builders and wrappers for repo view, fork, rename, enabling issues, issue cleanup, PR cleanup, issue creation with returned number, and main ref updates.
- Create `tools/swecontext_materializer/active_repo.py`
  - Implement `activate_task()` orchestration.
- Modify `tools/swecontext_materializer/cli.py`
  - Add `activate-task` command and cleanup flags.
- Modify `tools/swecontext_materializer/README.md`
  - Document the active upstream repo workflow.
- Add/update tests under `tests/swecontext_materializer/`.

---

### Task 1: Naming Helpers

**Files:**
- Create: `tools/swecontext_materializer/naming.py`
- Test: `tests/swecontext_materializer/test_naming.py`

- [ ] **Step 1: Write failing naming tests**

Create `tests/swecontext_materializer/test_naming.py`:

```python
from tools.swecontext_materializer.naming import active_repo_name, task_number
from tools.swecontext_materializer.models import TaskManifest


def make_task(instance_id: str, repo: str) -> TaskManifest:
    return TaskManifest(
        instance_id=instance_id,
        repo=repo,
        base_commit="abc123",
        problem_statement="Title\nBody",
        issue_title="Title",
        issue_body="Title\nBody",
        target_owner="wosuzyb",
        target_repo=instance_id,
    )


def test_task_number_uses_suffix_after_last_dash() -> None:
    assert task_number("astropy__astropy-15082") == "15082"
    assert task_number("scikit-learn__scikit-learn-25365") == "25365"


def test_active_repo_name_uses_upstream_repo_name_and_task_number() -> None:
    assert active_repo_name(make_task("astropy__astropy-15082", "astropy/astropy")) == "astropy-15082"
    assert active_repo_name(make_task("django__django-30153", "django/django")) == "django-30153"
    assert (
        active_repo_name(make_task("scikit-learn__scikit-learn-25365", "scikit-learn/scikit-learn"))
        == "scikit-learn-25365"
    )
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_naming.py -q
```

Expected: FAIL because `naming.py` does not exist.

- [ ] **Step 3: Implement naming helpers**

Create `tools/swecontext_materializer/naming.py`:

```python
from __future__ import annotations

from .models import TaskManifest


def task_number(instance_id: str) -> str:
    if "-" not in instance_id:
        raise ValueError(f"instance_id has no task number suffix: {instance_id}")
    return instance_id.rsplit("-", 1)[1]


def active_repo_name(task: TaskManifest) -> str:
    repo_name = task.repo.split("/", 1)[1]
    return f"{repo_name}-{task_number(task.instance_id)}"
```

- [ ] **Step 4: Run test and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_naming.py -q
```

Expected: PASS.

---

### Task 2: GitHub Operation Builders

**Files:**
- Modify: `tools/swecontext_materializer/github_ops.py`
- Test: `tests/swecontext_materializer/test_github_ops.py`

- [ ] **Step 1: Add failing tests for active repo GitHub commands**

Append to `tests/swecontext_materializer/test_github_ops.py`:

```python
from tools.swecontext_materializer.github_ops import (
    close_issue_args,
    close_pr_args,
    delete_ref_args,
    enable_issues_args,
    fork_repo_args,
    list_open_issues_args,
    list_open_prs_args,
    rename_repo_args,
    update_main_ref_args,
)


def test_active_repo_command_builders() -> None:
    assert fork_repo_args("astropy/astropy") == ["gh", "repo", "fork", "astropy/astropy", "--remote=false"]
    assert rename_repo_args("wosuzyb", "astropy", "astropy-15082") == [
        "gh",
        "api",
        "-X",
        "PATCH",
        "repos/wosuzyb/astropy",
        "-f",
        "name=astropy-15082",
    ]
    assert enable_issues_args("wosuzyb", "astropy-15082") == [
        "gh",
        "api",
        "-X",
        "PATCH",
        "repos/wosuzyb/astropy-15082",
        "-F",
        "has_issues=true",
    ]
    assert update_main_ref_args("wosuzyb", "astropy-15082", "abc123") == [
        "gh",
        "api",
        "-X",
        "PATCH",
        "repos/wosuzyb/astropy-15082/git/refs/heads/main",
        "-f",
        "sha=abc123",
        "-F",
        "force=true",
    ]
    assert list_open_issues_args("wosuzyb", "astropy-15082") == [
        "gh",
        "issue",
        "list",
        "--repo",
        "wosuzyb/astropy-15082",
        "--state",
        "open",
        "--json",
        "number,title",
        "--limit",
        "1000",
    ]
    assert close_issue_args("wosuzyb", "astropy-15082", 1) == [
        "gh",
        "issue",
        "close",
        "1",
        "--repo",
        "wosuzyb/astropy-15082",
    ]
    assert list_open_prs_args("wosuzyb", "astropy-15082") == [
        "gh",
        "pr",
        "list",
        "--repo",
        "wosuzyb/astropy-15082",
        "--state",
        "open",
        "--json",
        "number,headRefName,headRepositoryOwner",
        "--limit",
        "1000",
    ]
    assert close_pr_args("wosuzyb", "astropy-15082", 7) == [
        "gh",
        "pr",
        "close",
        "7",
        "--repo",
        "wosuzyb/astropy-15082",
    ]
    assert delete_ref_args("wosuzyb", "astropy-15082", "task-branch") == [
        "gh",
        "api",
        "-X",
        "DELETE",
        "repos/wosuzyb/astropy-15082/git/refs/heads/task-branch",
    ]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_github_ops.py -q
```

Expected: FAIL because the new functions do not exist.

- [ ] **Step 3: Implement command builders**

Modify `tools/swecontext_materializer/github_ops.py` by adding:

```python
def fork_repo_args(upstream_repo: str) -> list[str]:
    return ["gh", "repo", "fork", upstream_repo, "--remote=false"]


def rename_repo_args(owner: str, current_name: str, new_name: str) -> list[str]:
    return ["gh", "api", "-X", "PATCH", f"repos/{owner}/{current_name}", "-f", f"name={new_name}"]


def enable_issues_args(owner: str, repo_name: str) -> list[str]:
    return ["gh", "api", "-X", "PATCH", f"repos/{owner}/{repo_name}", "-F", "has_issues=true"]


def update_main_ref_args(owner: str, repo_name: str, sha: str) -> list[str]:
    return [
        "gh",
        "api",
        "-X",
        "PATCH",
        f"repos/{owner}/{repo_name}/git/refs/heads/main",
        "-f",
        f"sha={sha}",
        "-F",
        "force=true",
    ]


def list_open_issues_args(owner: str, repo_name: str) -> list[str]:
    return [
        "gh",
        "issue",
        "list",
        "--repo",
        f"{owner}/{repo_name}",
        "--state",
        "open",
        "--json",
        "number,title",
        "--limit",
        "1000",
    ]


def close_issue_args(owner: str, repo_name: str, number: int) -> list[str]:
    return ["gh", "issue", "close", str(number), "--repo", f"{owner}/{repo_name}"]


def list_open_prs_args(owner: str, repo_name: str) -> list[str]:
    return [
        "gh",
        "pr",
        "list",
        "--repo",
        f"{owner}/{repo_name}",
        "--state",
        "open",
        "--json",
        "number,headRefName,headRepositoryOwner",
        "--limit",
        "1000",
    ]


def close_pr_args(owner: str, repo_name: str, number: int) -> list[str]:
    return ["gh", "pr", "close", str(number), "--repo", f"{owner}/{repo_name}"]


def delete_ref_args(owner: str, repo_name: str, branch: str) -> list[str]:
    return ["gh", "api", "-X", "DELETE", f"repos/{owner}/{repo_name}/git/refs/heads/{branch}"]
```

- [ ] **Step 4: Run test and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_github_ops.py -q
```

Expected: PASS.

---

### Task 3: GitHub Active Repo Wrappers

**Files:**
- Modify: `tools/swecontext_materializer/models.py`
- Modify: `tools/swecontext_materializer/github_ops.py`
- Test: `tests/swecontext_materializer/test_github_active_wrappers.py`

- [ ] **Step 1: Write tests with a fake runner**

Create `tests/swecontext_materializer/test_github_active_wrappers.py`:

```python
import json

from tools.swecontext_materializer.github_ops import (
    close_open_issues,
    close_open_prs,
    create_issue_return_number,
    find_existing_fork_name,
)


class FakeRunner:
    def __init__(self, outputs: dict[str, str]):
        self.outputs = outputs
        self.calls: list[list[str]] = []

    def __call__(self, args, cwd=None, dry_run=False):
        from tools.swecontext_materializer.commands import CommandResult

        self.calls.append(args)
        key = " ".join(args)
        return CommandResult(args=args, returncode=0, stdout=self.outputs.get(key, ""), stderr="")


def test_find_existing_fork_name_returns_matching_parent() -> None:
    repos = [
        {"name": "astropy-15082", "isFork": True, "parent": {"nameWithOwner": "astropy/astropy"}},
        {"name": "other", "isFork": False, "parent": None},
    ]
    runner = FakeRunner({"gh repo list wosuzyb --json name,isFork,parent --limit 1000": json.dumps(repos)})

    assert find_existing_fork_name("wosuzyb", "astropy/astropy", runner=runner) == "astropy-15082"


def test_close_open_issues_closes_all_open_issues() -> None:
    runner = FakeRunner(
        {
            "gh issue list --repo wosuzyb/astropy-15082 --state open --json number,title --limit 1000": json.dumps(
                [{"number": 1, "title": "old"}, {"number": 2, "title": "older"}]
            )
        }
    )

    closed = close_open_issues("wosuzyb", "astropy-15082", runner=runner)

    assert closed == [1, 2]
    assert ["gh", "issue", "close", "1", "--repo", "wosuzyb/astropy-15082"] in runner.calls
    assert ["gh", "issue", "close", "2", "--repo", "wosuzyb/astropy-15082"] in runner.calls


def test_close_open_prs_can_delete_wosuzyb_branches() -> None:
    runner = FakeRunner(
        {
            "gh pr list --repo wosuzyb/astropy-15082 --state open --json number,headRefName,headRepositoryOwner --limit 1000": json.dumps(
                [{"number": 7, "headRefName": "task-branch", "headRepositoryOwner": {"login": "wosuzyb"}}]
            )
        }
    )

    closed = close_open_prs("wosuzyb", "astropy-15082", delete_branches=True, runner=runner)

    assert closed == [7]
    assert ["gh", "pr", "close", "7", "--repo", "wosuzyb/astropy-15082"] in runner.calls
    assert ["gh", "api", "-X", "DELETE", "repos/wosuzyb/astropy-15082/git/refs/heads/task-branch"] in runner.calls


def test_create_issue_return_number_parses_url() -> None:
    runner = FakeRunner(
        {
            "gh issue create --repo wosuzyb/astropy-15082 --title Title --body Body": "https://github.com/wosuzyb/astropy-15082/issues/12\n"
        }
    )

    assert create_issue_return_number("wosuzyb", "astropy-15082", "Title", "Body", runner=runner) == 12
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_github_active_wrappers.py -q
```

Expected: FAIL because wrappers do not exist.

- [ ] **Step 3: Add `ActivationResult`**

Modify `tools/swecontext_materializer/models.py`:

```python
@dataclass(frozen=True)
class ActivationResult:
    instance_id: str
    upstream_repo: str
    active_repo: str
    base_commit: str
    issue_number: int | None
    closed_issues: list[int] = field(default_factory=list)
    closed_prs: list[int] = field(default_factory=list)
```

- [ ] **Step 4: Implement wrappers**

Modify `tools/swecontext_materializer/github_ops.py` by importing `json`, `re`, `Callable`, and adding:

```python
from collections.abc import Callable
import json
import re

Runner = Callable[[list[str], object | None, bool], object]


def _run(args: list[str], runner=None, dry_run: bool = False):
    return (runner or run_command)(args, cwd=None, dry_run=dry_run)


def find_existing_fork_name(owner: str, upstream_repo: str, runner=None, dry_run: bool = False) -> str | None:
    result = _run(["gh", "repo", "list", owner, "--json", "name,isFork,parent", "--limit", "1000"], runner, dry_run)
    if dry_run:
        return None
    for repo in json.loads(result.stdout or "[]"):
        parent = repo.get("parent") or {}
        if repo.get("isFork") and parent.get("nameWithOwner") == upstream_repo:
            return repo["name"]
    return None


def ensure_issues_enabled(owner: str, repo_name: str, runner=None, dry_run: bool = False) -> None:
    _run(enable_issues_args(owner, repo_name), runner, dry_run)


def rename_repo(owner: str, current_name: str, new_name: str, runner=None, dry_run: bool = False) -> None:
    if current_name == new_name:
        return
    _run(rename_repo_args(owner, current_name, new_name), runner, dry_run)


def fork_repo(upstream_repo: str, runner=None, dry_run: bool = False) -> None:
    _run(fork_repo_args(upstream_repo), runner, dry_run)


def update_main_ref(owner: str, repo_name: str, sha: str, runner=None, dry_run: bool = False) -> None:
    _run(update_main_ref_args(owner, repo_name, sha), runner, dry_run)


def close_open_issues(owner: str, repo_name: str, runner=None, dry_run: bool = False) -> list[int]:
    result = _run(list_open_issues_args(owner, repo_name), runner, dry_run)
    if dry_run:
        return []
    issues = json.loads(result.stdout or "[]")
    closed: list[int] = []
    for issue in issues:
        number = int(issue["number"])
        _run(close_issue_args(owner, repo_name, number), runner, dry_run)
        closed.append(number)
    return closed


def close_open_prs(owner: str, repo_name: str, delete_branches: bool, runner=None, dry_run: bool = False) -> list[int]:
    result = _run(list_open_prs_args(owner, repo_name), runner, dry_run)
    if dry_run:
        return []
    prs = json.loads(result.stdout or "[]")
    closed: list[int] = []
    for pr in prs:
        number = int(pr["number"])
        _run(close_pr_args(owner, repo_name, number), runner, dry_run)
        closed.append(number)
        head_owner = (pr.get("headRepositoryOwner") or {}).get("login")
        head_ref = pr.get("headRefName")
        if delete_branches and head_owner == owner and head_ref:
            _run(delete_ref_args(owner, repo_name, head_ref), runner, dry_run)
    return closed


def create_issue_return_number(owner: str, repo_name: str, title: str, body: str, runner=None, dry_run: bool = False) -> int | None:
    result = _run(
        ["gh", "issue", "create", "--repo", f"{owner}/{repo_name}", "--title", title, "--body", body],
        runner,
        dry_run,
    )
    if dry_run:
        return None
    match = re.search(r"/issues/(\\d+)", result.stdout)
    if not match:
        raise ValueError(f"could not parse issue number from gh output: {result.stdout!r}")
    return int(match.group(1))
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_github_active_wrappers.py tests/swecontext_materializer/test_github_ops.py -q
```

Expected: PASS.

---

### Task 4: Activation Orchestration

**Files:**
- Create: `tools/swecontext_materializer/active_repo.py`
- Test: `tests/swecontext_materializer/test_active_repo.py`

- [ ] **Step 1: Write activation tests with monkeypatches**

Create `tests/swecontext_materializer/test_active_repo.py`:

```python
from tools.swecontext_materializer.active_repo import activate_task, find_task
from tools.swecontext_materializer.models import TaskManifest


def task(instance_id="astropy__astropy-15082") -> TaskManifest:
    return TaskManifest(
        instance_id=instance_id,
        repo="astropy/astropy",
        base_commit="abc123",
        problem_statement="Title\nBody",
        issue_title="Title",
        issue_body="Title\nBody",
        target_owner="wosuzyb",
        target_repo=instance_id,
    )


def test_find_task_returns_matching_manifest_entry() -> None:
    assert find_task([task()], "astropy__astropy-15082").base_commit == "abc123"


def test_find_task_raises_for_missing_instance_id() -> None:
    try:
        find_task([task()], "missing")
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_activate_task_reuses_existing_target_repo(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr("tools.swecontext_materializer.active_repo.repo_exists_by_name", lambda owner, name, dry_run=False: True)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.find_existing_fork_name", lambda owner, upstream, dry_run=False: None)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.rename_repo", lambda *args, **kwargs: calls.append(("rename", args)))
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.fork_repo", lambda *args, **kwargs: calls.append(("fork", args)))
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.ensure_issues_enabled", lambda *args, **kwargs: calls.append(("enable_issues", args)))
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.close_open_issues", lambda *args, **kwargs: [1])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.close_open_prs", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.update_main_ref", lambda *args, **kwargs: calls.append(("update_ref", args)))
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.create_issue_return_number", lambda *args, **kwargs: 2)

    result = activate_task([task()], "astropy__astropy-15082", cleanup_issues="close", cleanup_prs="none")

    assert result.active_repo == "wosuzyb/astropy-15082"
    assert result.issue_number == 2
    assert result.closed_issues == [1]
    assert ("fork", ("astropy/astropy",)) not in calls
    assert ("update_ref", ("wosuzyb", "astropy-15082", "abc123")) in calls


def test_activate_task_renames_existing_fork_when_target_missing(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr("tools.swecontext_materializer.active_repo.repo_exists_by_name", lambda owner, name, dry_run=False: False)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.find_existing_fork_name", lambda owner, upstream, dry_run=False: "astropy-4973")
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.rename_repo", lambda *args, **kwargs: calls.append(("rename", args)))
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.fork_repo", lambda *args, **kwargs: calls.append(("fork", args)))
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.ensure_issues_enabled", lambda *args, **kwargs: None)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.close_open_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.close_open_prs", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.update_main_ref", lambda *args, **kwargs: None)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.create_issue_return_number", lambda *args, **kwargs: 3)

    activate_task([task()], "astropy__astropy-15082")

    assert ("rename", ("wosuzyb", "astropy-4973", "astropy-15082")) in calls
    assert not any(name == "fork" for name, _ in calls)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_active_repo.py -q
```

Expected: FAIL because `active_repo.py` does not exist.

- [ ] **Step 3: Implement activation orchestration**

Create `tools/swecontext_materializer/active_repo.py`:

```python
from __future__ import annotations

from .github_ops import (
    close_open_issues,
    close_open_prs,
    create_issue_return_number,
    ensure_issues_enabled,
    find_existing_fork_name,
    fork_repo,
    repo_exists_by_name,
    rename_repo,
    update_main_ref,
)
from .models import ActivationResult, TaskManifest
from .naming import active_repo_name


def find_task(tasks: list[TaskManifest], instance_id: str) -> TaskManifest:
    for task in tasks:
        if task.instance_id == instance_id:
            return task
    raise ValueError(f"manifest does not contain instance_id: {instance_id}")


def activate_task(
    tasks: list[TaskManifest],
    instance_id: str,
    cleanup_issues: str = "close",
    cleanup_prs: str = "none",
    dry_run: bool = False,
) -> ActivationResult:
    task = find_task(tasks, instance_id)
    owner = task.target_owner
    target_repo = active_repo_name(task)

    if not repo_exists_by_name(owner, target_repo, dry_run=dry_run):
        existing_fork = find_existing_fork_name(owner, task.repo, dry_run=dry_run)
        if existing_fork:
            rename_repo(owner, existing_fork, target_repo, dry_run=dry_run)
        else:
            fork_repo(task.repo, dry_run=dry_run)
            upstream_repo_name = task.repo.split("/", 1)[1]
            rename_repo(owner, upstream_repo_name, target_repo, dry_run=dry_run)

    ensure_issues_enabled(owner, target_repo, dry_run=dry_run)

    closed_issues: list[int] = []
    if cleanup_issues == "close":
        closed_issues = close_open_issues(owner, target_repo, dry_run=dry_run)
    elif cleanup_issues != "none":
        raise ValueError(f"unknown cleanup_issues value: {cleanup_issues}")

    closed_prs: list[int] = []
    if cleanup_prs == "close":
        closed_prs = close_open_prs(owner, target_repo, delete_branches=False, dry_run=dry_run)
    elif cleanup_prs == "close-and-delete-branches":
        closed_prs = close_open_prs(owner, target_repo, delete_branches=True, dry_run=dry_run)
    elif cleanup_prs != "none":
        raise ValueError(f"unknown cleanup_prs value: {cleanup_prs}")

    update_main_ref(owner, target_repo, task.base_commit, dry_run=dry_run)
    issue_number = create_issue_return_number(owner, target_repo, task.issue_title, task.issue_body, dry_run=dry_run)

    return ActivationResult(
        instance_id=task.instance_id,
        upstream_repo=task.repo,
        active_repo=f"{owner}/{target_repo}",
        base_commit=task.base_commit,
        issue_number=issue_number,
        closed_issues=closed_issues,
        closed_prs=closed_prs,
    )
```

- [ ] **Step 4: Add missing `repo_exists_by_name` wrapper**

Modify `tools/swecontext_materializer/github_ops.py`:

```python
def repo_exists_by_name(owner: str, repo_name: str, dry_run: bool = False) -> bool:
    try:
        run_command(["gh", "repo", "view", f"{owner}/{repo_name}"], cwd=None, dry_run=dry_run)
        return True
    except CommandError:
        return False
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_active_repo.py -q
```

Expected: PASS.

---

### Task 5: CLI Integration And Status Recording

**Files:**
- Modify: `tools/swecontext_materializer/cli.py`
- Modify: `tools/swecontext_materializer/status.py`
- Test: `tests/swecontext_materializer/test_cli.py`

- [ ] **Step 1: Add failing CLI test for `activate-task`**

Append to `tests/swecontext_materializer/test_cli.py`:

```python
def test_activate_task_command_records_activation(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.jsonl"
    status = tmp_path / "status.json"
    manifest.write_text(
        json.dumps(
            {
                "instance_id": "astropy__astropy-15082",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "problem_statement": "Title\nBody",
                "issue_title": "Title",
                "issue_body": "Title\nBody",
                "target_owner": "wosuzyb",
                "target_repo": "astropy__astropy-15082",
                "related_pr_url": None,
                "related_issue_url": None,
                "experience_instance_ids": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    from tools.swecontext_materializer.models import ActivationResult

    def fake_activate_task(tasks, instance_id, cleanup_issues, cleanup_prs, dry_run):
        return ActivationResult(
            instance_id=instance_id,
            upstream_repo="astropy/astropy",
            active_repo="wosuzyb/astropy-15082",
            base_commit="abc123",
            issue_number=4,
            closed_issues=[1],
            closed_prs=[],
        )

    monkeypatch.setattr("tools.swecontext_materializer.cli.activate_task", fake_activate_task)

    exit_code = main(
        [
            "activate-task",
            "--manifest",
            str(manifest),
            "--status-file",
            str(status),
            "--instance-id",
            "astropy__astropy-15082",
        ]
    )

    assert exit_code == 0
    data = json.loads(status.read_text(encoding="utf-8"))
    assert data["astropy__astropy-15082"]["stage"] == "task_activated"
    assert data["astropy__astropy-15082"]["active_repo"] == "wosuzyb/astropy-15082"
    assert data["astropy__astropy-15082"]["issue_number"] == 4
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_cli.py -q
```

Expected: FAIL because CLI has no `activate-task`.

- [ ] **Step 3: Add status helper**

Modify `tools/swecontext_materializer/status.py`:

```python
    def record_activation(self, instance_id: str, payload: dict) -> None:
        self._data.setdefault(instance_id, {})
        self._data[instance_id].update(payload)
        self._data[instance_id]["stage"] = "task_activated"
        self._data[instance_id].pop("error", None)
        self._save()
```

- [ ] **Step 4: Add CLI command**

Modify `tools/swecontext_materializer/cli.py`:

```python
from .active_repo import activate_task
```

Add command function:

```python
def cmd_activate_task(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    tasks = read_manifest_jsonl(args.manifest)
    try:
        result = activate_task(
            tasks,
            args.instance_id,
            cleanup_issues=args.cleanup_issues,
            cleanup_prs=args.cleanup_prs,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            status.record_activation(
                result.instance_id,
                {
                    "upstream_repo": result.upstream_repo,
                    "active_repo": result.active_repo,
                    "base_commit": result.base_commit,
                    "issue_number": result.issue_number,
                    "closed_issues": result.closed_issues,
                    "closed_prs": result.closed_prs,
                    "cleanup_issues": args.cleanup_issues,
                    "cleanup_prs": args.cleanup_prs,
                },
            )
        print(f"{result.instance_id}: activated {result.active_repo} issue={result.issue_number}")
        return 0
    except Exception as exc:
        status.fail(args.instance_id, "activate_failed", str(exc))
        print(f"{args.instance_id}: activate_failed: {exc}")
        return 1
```

Add parser:

```python
    activate = subparsers.add_parser("activate-task")
    activate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    activate.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    activate.add_argument("--instance-id", required=True)
    activate.add_argument("--cleanup-issues", choices=["none", "close"], default="close")
    activate.add_argument(
        "--cleanup-prs",
        choices=["none", "close", "close-and-delete-branches"],
        default="none",
    )
    activate.add_argument("--dry-run", action="store_true")
    activate.set_defaults(func=cmd_activate_task)
```

- [ ] **Step 5: Run CLI tests and verify pass**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer/test_cli.py -q
```

Expected: PASS.

---

### Task 6: Documentation And Verification

**Files:**
- Modify: `tools/swecontext_materializer/README.md`

- [ ] **Step 1: Update README**

Append to `tools/swecontext_materializer/README.md`:

```markdown
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
- close old open issues by default
- leave open PRs alone by default
- force `main` to the task `base_commit`
- create a new issue from `problem_statement`

Cleanup controls:

```bash
--cleanup-issues none
--cleanup-issues close
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
```

- [ ] **Step 2: Run all unit tests**

Run:

```bash
uv run --with pytest pytest tests/swecontext_materializer -q
```

Expected: PASS.

- [ ] **Step 3: Run manifest preparation**

Run:

```bash
python3 -m tools.swecontext_materializer.cli prepare-manifest
```

Expected:

```text
planned_tasks=99
output=generated/swecontextbench-lite/manifest.jsonl
```

- [ ] **Step 4: Dry-run activation**

Run:

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082 \
  --dry-run
```

Expected: exits 0 and prints an activation line without GitHub writes.

- [ ] **Step 5: Real smoke test**

Only run after explicit user approval:

First inspect whether the existing smoke-test fork is still named with the old convention:

```bash
gh repo view wosuzyb/astropy__astropy-15082 --json nameWithOwner,isFork,parent,defaultBranchRef,hasIssuesEnabled
gh repo view wosuzyb/astropy-15082 --json nameWithOwner,isFork,parent,defaultBranchRef,hasIssuesEnabled
```

If `wosuzyb/astropy__astropy-15082` exists and `wosuzyb/astropy-15082` does not, rename the old-convention repo to the new active name before running the command:

```bash
gh api -X PATCH repos/wosuzyb/astropy__astropy-15082 -f name=astropy-15082
```

Then run:

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082
```

Expected:

- repo `wosuzyb/astropy-15082` exists or is created/renamed
- it is a fork of `astropy/astropy`
- issues are enabled
- `main` points to `c5e2521db013d9641999be9c79d1d807741bc39a`
- one new issue is created from `problem_statement`

---

## Self-Review Notes

- Spec coverage:
  - active repo naming: Task 1.
  - target repo reuse: Task 4.
  - existing fork rename or new fork creation: Task 4.
  - enabling issues: Tasks 2 and 4.
  - issue cleanup switch: Tasks 3 and 4.
  - PR cleanup switch: Tasks 3 and 4.
  - move `main` to `base_commit`: Tasks 2 and 4.
  - CLI and status recording: Task 5.
  - docs and verification: Task 6.
- Placeholder scan: no placeholder tasks or unspecified code blocks remain.
- Type consistency: `ActivationResult`, `TaskManifest`, and cleanup option strings are consistent across tasks.
