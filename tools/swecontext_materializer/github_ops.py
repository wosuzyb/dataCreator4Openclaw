from __future__ import annotations

import json
import re
from collections.abc import Callable

from .commands import CommandError, run_command
from .models import TaskManifest


Runner = Callable[[list[str], object | None, bool], object]


def full_repo_name(task: TaskManifest) -> str:
    return f"{task.target_owner}/{task.target_repo}"


def repo_view_args(task: TaskManifest) -> list[str]:
    return ["gh", "repo", "view", full_repo_name(task)]


def create_repo_args(task: TaskManifest) -> list[str]:
    return ["gh", "repo", "create", full_repo_name(task), "--public"]


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
        "id,number,title",
        "--limit",
        "1000",
    ]


def delete_issue_args(issue_id: str) -> list[str]:
    return [
        "gh",
        "api",
        "graphql",
        "-f",
        "query=mutation($id: ID!) { deleteIssue(input: { issueId: $id }) { clientMutationId } }",
        "-f",
        f"id={issue_id}",
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


def list_branches_args(owner: str, repo_name: str) -> list[str]:
    return [
        "gh",
        "api",
        f"repos/{owner}/{repo_name}/branches",
        "--paginate",
        "--jq",
        ".[].name",
    ]


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


def delete_open_issues(owner: str, repo_name: str, runner=None, dry_run: bool = False) -> list[int]:
    result = _run(list_open_issues_args(owner, repo_name), runner, dry_run)
    if dry_run:
        return []
    issues = json.loads(result.stdout or "[]")
    deleted: list[int] = []
    for issue in issues:
        issue_id = issue.get("id")
        if not issue_id:
            raise ValueError(f"open issue is missing node id: {issue!r}")
        _run(delete_issue_args(issue_id), runner, dry_run)
        deleted.append(int(issue["number"]))
    return deleted


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


def delete_branches_except_main(owner: str, repo_name: str, runner=None, dry_run: bool = False) -> list[str]:
    result = _run(list_branches_args(owner, repo_name), runner, dry_run)
    if dry_run:
        return []
    branches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    deleted: list[str] = []
    for branch in branches:
        if branch == "main":
            continue
        _run(delete_ref_args(owner, repo_name, branch), runner, dry_run)
        deleted.append(branch)
    return deleted


def create_issue_return_number(
    owner: str,
    repo_name: str,
    title: str,
    body: str,
    runner=None,
    dry_run: bool = False,
) -> int | None:
    result = _run(
        ["gh", "issue", "create", "--repo", f"{owner}/{repo_name}", "--title", title, "--body", body],
        runner,
        dry_run,
    )
    if dry_run:
        return None
    match = re.search(r"/issues/(\d+)", result.stdout)
    if not match:
        raise ValueError(f"could not parse issue number from gh output: {result.stdout!r}")
    return int(match.group(1))


def repo_exists(task: TaskManifest, dry_run: bool = False) -> bool:
    try:
        run_command(repo_view_args(task), cwd=None, dry_run=dry_run)
        return True
    except CommandError:
        return False


def repo_exists_by_name(owner: str, repo_name: str, dry_run: bool = False) -> bool:
    try:
        run_command(["gh", "repo", "view", f"{owner}/{repo_name}"], cwd=None, dry_run=dry_run)
        return True
    except CommandError:
        return False


def create_repo(task: TaskManifest, dry_run: bool = False) -> str:
    if dry_run:
        return "dry_run"
    if repo_exists(task, dry_run=dry_run):
        return "already_present"
    run_command(create_repo_args(task), cwd=None, dry_run=dry_run)
    return "created"


def create_issue(task: TaskManifest, dry_run: bool = False) -> None:
    run_command(create_issue_args(task), cwd=None, dry_run=dry_run)
