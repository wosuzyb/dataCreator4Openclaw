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
