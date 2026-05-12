from __future__ import annotations

from .models import TaskManifest


def task_number(instance_id: str) -> str:
    if "-" not in instance_id:
        raise ValueError(f"instance_id has no task number suffix: {instance_id}")
    return instance_id.rsplit("-", 1)[1]


def active_repo_name(task: TaskManifest) -> str:
    repo_name = task.repo.split("/", 1)[1]
    return f"{repo_name}-{task_number(task.instance_id)}"
