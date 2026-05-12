from pathlib import Path

import pytest

from tools.swecontext_materializer.commands import CommandError, run_command
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
