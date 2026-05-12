from tools.swecontext_materializer.github_ops import (
    close_issue_args,
    close_pr_args,
    create_issue_args,
    create_main_ref_args,
    create_repo,
    create_repo_args,
    delete_issue_args,
    delete_ref_args,
    enable_issues_args,
    fork_repo_args,
    get_default_branch_args,
    list_branches_args,
    list_open_issues_args,
    list_open_prs_args,
    list_tags_args,
    rename_repo_args,
    repo_view_args,
    set_default_branch_args,
    update_branch_ref_args,
    update_main_ref_args,
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


def test_create_repo_args_public_under_owner() -> None:
    assert create_repo_args(task()) == [
        "gh",
        "repo",
        "create",
        "wosuzyb/astropy__astropy-15082",
        "--public",
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


def test_create_repo_dry_run_reports_dry_run() -> None:
    assert create_repo(task(), dry_run=True) == "dry_run"


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
    assert create_main_ref_args("wosuzyb", "astropy-15082", "abc123") == [
        "gh",
        "api",
        "-X",
        "POST",
        "repos/wosuzyb/astropy-15082/git/refs",
        "-f",
        "ref=refs/heads/main",
        "-f",
        "sha=abc123",
    ]
    assert set_default_branch_args("wosuzyb", "astropy-15082", "main") == [
        "gh",
        "api",
        "-X",
        "PATCH",
        "repos/wosuzyb/astropy-15082",
        "-f",
        "default_branch=main",
    ]
    assert get_default_branch_args("wosuzyb", "sympy-11275") == [
        "gh",
        "api",
        "repos/wosuzyb/sympy-11275",
        "--jq",
        ".default_branch",
    ]
    assert update_branch_ref_args("wosuzyb", "sympy-11275", "master", "abc123") == [
        "gh",
        "api",
        "-X",
        "PATCH",
        "repos/wosuzyb/sympy-11275/git/refs/heads/master",
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
        "id,number,title",
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


def test_delete_cleanup_command_builders() -> None:
    assert list_open_issues_args("wosuzyb", "astropy-15082") == [
        "gh",
        "issue",
        "list",
        "--repo",
        "wosuzyb/astropy-15082",
        "--state",
        "open",
        "--json",
        "id,number,title",
        "--limit",
        "1000",
    ]
    assert delete_issue_args("issue-node-id") == [
        "gh",
        "api",
        "graphql",
        "-f",
        "query=mutation($id: ID!) { deleteIssue(input: { issueId: $id }) { clientMutationId } }",
        "-f",
        "id=issue-node-id",
    ]
    assert list_branches_args("wosuzyb", "astropy-15082") == [
        "gh",
        "api",
        "repos/wosuzyb/astropy-15082/branches",
        "--paginate",
        "--jq",
        ".[].name",
    ]
    assert list_tags_args("wosuzyb", "astropy-15082") == [
        "gh",
        "api",
        "repos/wosuzyb/astropy-15082/tags",
        "--paginate",
        "--jq",
        ".[].name",
    ]
    assert delete_ref_args("wosuzyb", "astropy-15082", "tags/v1.0") == [
        "gh",
        "api",
        "-X",
        "DELETE",
        "repos/wosuzyb/astropy-15082/git/refs/tags/v1.0",
    ]
