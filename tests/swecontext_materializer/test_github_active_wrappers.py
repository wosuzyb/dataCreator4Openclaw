import json

from tools.swecontext_materializer.github_ops import (
    close_open_issues,
    close_open_prs,
    create_issue_return_number,
    delete_branches_except_main,
    delete_open_issues,
    delete_tags,
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
            "gh issue list --repo wosuzyb/astropy-15082 --state open --json id,number,title --limit 1000": json.dumps(
                [{"number": 1, "title": "old"}, {"number": 2, "title": "older"}]
            )
        }
    )

    closed = close_open_issues("wosuzyb", "astropy-15082", runner=runner)

    assert closed == [1, 2]
    assert ["gh", "issue", "close", "1", "--repo", "wosuzyb/astropy-15082"] in runner.calls
    assert ["gh", "issue", "close", "2", "--repo", "wosuzyb/astropy-15082"] in runner.calls


def test_delete_open_issues_deletes_all_open_issues_by_node_id() -> None:
    runner = FakeRunner(
        {
            "gh issue list --repo wosuzyb/astropy-15082 --state open --json id,number,title --limit 1000": json.dumps(
                [
                    {"id": "ISSUE_1", "number": 1, "title": "old"},
                    {"id": "ISSUE_2", "number": 2, "title": "older"},
                ]
            )
        }
    )

    deleted = delete_open_issues("wosuzyb", "astropy-15082", runner=runner)

    assert deleted == [1, 2]
    assert [
        "gh",
        "api",
        "graphql",
        "-f",
        "query=mutation($id: ID!) { deleteIssue(input: { issueId: $id }) { clientMutationId } }",
        "-f",
        "id=ISSUE_1",
    ] in runner.calls
    assert [
        "gh",
        "api",
        "graphql",
        "-f",
        "query=mutation($id: ID!) { deleteIssue(input: { issueId: $id }) { clientMutationId } }",
        "-f",
        "id=ISSUE_2",
    ] in runner.calls


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


def test_delete_branches_except_main_removes_every_other_branch() -> None:
    runner = FakeRunner(
        {
            "gh api repos/wosuzyb/astropy-15082/branches --paginate --jq .[].name": (
                "main\nold-task\nfeature/test\n"
            )
        }
    )

    deleted = delete_branches_except_main("wosuzyb", "astropy-15082", runner=runner)

    assert deleted == ["old-task", "feature/test"]
    assert ["gh", "api", "-X", "DELETE", "repos/wosuzyb/astropy-15082/git/refs/heads/old-task"] in runner.calls
    assert ["gh", "api", "-X", "DELETE", "repos/wosuzyb/astropy-15082/git/refs/heads/feature/test"] in runner.calls


def test_delete_tags_removes_all_tags() -> None:
    runner = FakeRunner(
        {
            "gh api repos/wosuzyb/astropy-15082/tags --paginate --jq .[].name": (
                "v1.0\nrelease/2024\n"
            )
        }
    )

    deleted = delete_tags("wosuzyb", "astropy-15082", runner=runner)

    assert deleted == ["v1.0", "release/2024"]
    assert ["gh", "api", "-X", "DELETE", "repos/wosuzyb/astropy-15082/git/refs/tags/v1.0"] in runner.calls
    assert ["gh", "api", "-X", "DELETE", "repos/wosuzyb/astropy-15082/git/refs/tags/release/2024"] in runner.calls


def test_create_issue_return_number_parses_url() -> None:
    runner = FakeRunner(
        {
            "gh issue create --repo wosuzyb/astropy-15082 --title Title --body Body": (
                "https://github.com/wosuzyb/astropy-15082/issues/12\n"
            )
        }
    )

    assert create_issue_return_number("wosuzyb", "astropy-15082", "Title", "Body", runner=runner) == 12
