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
