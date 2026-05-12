from __future__ import annotations

from .github_ops import (
    close_open_prs,
    create_issue_return_number,
    delete_branches_except_main,
    delete_open_issues,
    delete_tags,
    ensure_issues_enabled,
    find_existing_fork_name,
    fork_repo,
    rename_repo,
    repo_exists_by_name,
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
    cleanup_issues: str = "delete",
    cleanup_prs: str = "close-and-delete-branches",
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

    deleted_issues: list[int] = []
    if cleanup_issues == "delete":
        deleted_issues = delete_open_issues(owner, target_repo, dry_run=dry_run)
    elif cleanup_issues == "none":
        pass
    elif cleanup_issues != "none":
        raise ValueError(f"unknown cleanup_issues value: {cleanup_issues}")

    closed_prs: list[int] = []
    if cleanup_prs == "close":
        closed_prs = close_open_prs(owner, target_repo, delete_branches=False, dry_run=dry_run)
    elif cleanup_prs == "close-and-delete-branches":
        closed_prs = close_open_prs(owner, target_repo, delete_branches=True, dry_run=dry_run)
    elif cleanup_prs != "none":
        raise ValueError(f"unknown cleanup_prs value: {cleanup_prs}")

    deleted_branches = delete_branches_except_main(owner, target_repo, dry_run=dry_run)
    deleted_tags = delete_tags(owner, target_repo, dry_run=dry_run)
    update_main_ref(owner, target_repo, task.base_commit, dry_run=dry_run)
    issue_number = create_issue_return_number(owner, target_repo, task.issue_title, task.issue_body, dry_run=dry_run)

    return ActivationResult(
        instance_id=task.instance_id,
        upstream_repo=task.repo,
        active_repo=f"{owner}/{target_repo}",
        base_commit=task.base_commit,
        issue_number=issue_number,
        deleted_issues=deleted_issues,
        closed_prs=closed_prs,
        deleted_branches=deleted_branches,
        deleted_tags=deleted_tags,
    )
