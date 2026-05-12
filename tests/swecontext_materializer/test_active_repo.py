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

    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.repo_exists_by_name",
        lambda owner, name, dry_run=False: True,
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.find_existing_fork_name",
        lambda owner, upstream, dry_run=False: None,
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.rename_repo",
        lambda *args, **kwargs: calls.append(("rename", args)),
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.fork_repo",
        lambda *args, **kwargs: calls.append(("fork", args)),
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.ensure_issues_enabled",
        lambda *args, **kwargs: calls.append(("enable_issues", args)),
    )
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.delete_open_issues", lambda *args, **kwargs: [1])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.close_open_prs", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.delete_branches_except_main", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.delete_tags", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.update_main_ref",
        lambda *args, **kwargs: calls.append(("update_ref", args)),
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.create_issue_return_number",
        lambda *args, **kwargs: 2,
    )

    result = activate_task([task()], "astropy__astropy-15082", cleanup_issues="delete", cleanup_prs="none")

    assert result.active_repo == "wosuzyb/astropy-15082"
    assert result.issue_number == 2
    assert result.deleted_issues == [1]
    assert ("fork", ("astropy/astropy",)) not in calls
    assert ("update_ref", ("wosuzyb", "astropy-15082", "abc123")) in calls


def test_activate_task_renames_existing_fork_when_target_missing(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.repo_exists_by_name",
        lambda owner, name, dry_run=False: False,
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.find_existing_fork_name",
        lambda owner, upstream, dry_run=False: "astropy-4973",
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.rename_repo",
        lambda *args, **kwargs: calls.append(("rename", args)),
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.fork_repo",
        lambda *args, **kwargs: calls.append(("fork", args)),
    )
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.ensure_issues_enabled", lambda *args, **kwargs: None)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.delete_open_issues", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.close_open_prs", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.delete_branches_except_main", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.delete_tags", lambda *args, **kwargs: [])
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.update_main_ref", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.create_issue_return_number",
        lambda *args, **kwargs: 3,
    )

    activate_task([task()], "astropy__astropy-15082")

    assert ("rename", ("wosuzyb", "astropy-4973", "astropy-15082")) in calls
    assert not any(name == "fork" for name, _ in calls)


def test_activate_task_strong_cleanup_deletes_issues_closes_prs_and_deletes_branches(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr("tools.swecontext_materializer.active_repo.repo_exists_by_name", lambda *args, **kwargs: True)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.find_existing_fork_name", lambda *args, **kwargs: None)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.ensure_issues_enabled", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.delete_open_issues",
        lambda *args, **kwargs: calls.append(("delete_issues", args)) or [1, 2],
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.close_open_prs",
        lambda *args, **kwargs: calls.append(("close_prs", args, kwargs)) or [3],
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.delete_branches_except_main",
        lambda *args, **kwargs: calls.append(("delete_branches", args)) or ["old-task"],
    )
    monkeypatch.setattr(
        "tools.swecontext_materializer.active_repo.delete_tags",
        lambda *args, **kwargs: calls.append(("delete_tags", args)) or ["v1.0"],
    )
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.update_main_ref", lambda *args, **kwargs: None)
    monkeypatch.setattr("tools.swecontext_materializer.active_repo.create_issue_return_number", lambda *args, **kwargs: 4)

    result = activate_task([task()], "astropy__astropy-15082")

    assert result.deleted_issues == [1, 2]
    assert result.closed_prs == [3]
    assert result.deleted_branches == ["old-task"]
    assert result.deleted_tags == ["v1.0"]
    assert ("delete_issues", ("wosuzyb", "astropy-15082")) in calls
    assert ("close_prs", ("wosuzyb", "astropy-15082"), {"delete_branches": True, "dry_run": False}) in calls
    assert ("delete_branches", ("wosuzyb", "astropy-15082")) in calls
    assert ("delete_tags", ("wosuzyb", "astropy-15082")) in calls
