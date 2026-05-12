from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .models import TaskManifest


def first_problem_statement_line(problem_statement: str) -> str:
    for line in problem_statement.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "SWEContextBench task"


def _read_related_jsonl(path: Path) -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            instance_id = row["instance_id"]
            if instance_id in tasks:
                raise ValueError(
                    f"duplicate instance_id in related JSONL at line {line_number}: {instance_id}"
                )
            tasks[instance_id] = row
    return tasks


def _read_relationships(path: Path) -> dict[str, dict]:
    relationships: dict[str, dict] = defaultdict(
        lambda: {
            "related_pr_url": None,
            "related_issue_url": None,
            "experience_instance_ids": [],
        }
    )
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            instance_id = row["related_instance_id"]
            entry = relationships[instance_id]
            entry["related_pr_url"] = entry["related_pr_url"] or row.get("related_pr_url")
            entry["related_issue_url"] = entry["related_issue_url"] or row.get("related_issue_url")
            experience_id = row.get("experience_instance_id")
            if experience_id and experience_id not in entry["experience_instance_ids"]:
                entry["experience_instance_ids"].append(experience_id)
    return dict(relationships)


def build_manifest(related_jsonl: Path, relationships_tsv: Path, owner: str) -> list[TaskManifest]:
    related_tasks = _read_related_jsonl(related_jsonl)
    relationships = _read_relationships(relationships_tsv)
    manifest: list[TaskManifest] = []

    for instance_id in sorted(related_tasks):
        task = related_tasks[instance_id]
        problem_statement = task["problem_statement"]
        relationship = relationships.get(instance_id, {})
        manifest.append(
            TaskManifest(
                instance_id=instance_id,
                repo=task["repo"],
                base_commit=task["base_commit"],
                problem_statement=problem_statement,
                issue_title=first_problem_statement_line(problem_statement),
                issue_body=problem_statement,
                target_owner=owner,
                target_repo=instance_id,
                related_pr_url=relationship.get("related_pr_url"),
                related_issue_url=relationship.get("related_issue_url"),
                experience_instance_ids=relationship.get("experience_instance_ids", []),
            )
        )

    return manifest


def write_manifest_jsonl(tasks: list[TaskManifest], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for task in tasks:
            handle.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")


def read_manifest_jsonl(path: Path) -> list[TaskManifest]:
    tasks: list[TaskManifest] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tasks.append(TaskManifest.from_dict(json.loads(line)))
    return tasks
