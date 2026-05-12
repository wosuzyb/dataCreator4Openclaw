from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .manifest import first_problem_statement_line
from .models import TaskManifest


def read_jsonl_tasks(path: Path) -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            instance_id = row["instance_id"]
            if instance_id in tasks:
                raise ValueError(f"duplicate instance_id in {path} at line {line_number}: {instance_id}")
            tasks[instance_id] = row
    return tasks


def read_one_to_one_links(relationships_tsv: Path) -> dict[str, str]:
    links: dict[str, set[str]] = defaultdict(set)
    with relationships_tsv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            related_id = row.get("related_instance_id")
            experience_id = row.get("experience_instance_id")
            if related_id and experience_id:
                links[related_id].add(experience_id)

    one_to_one: dict[str, str] = {}
    for related_id, experience_ids in links.items():
        if len(experience_ids) == 1:
            one_to_one[related_id] = next(iter(experience_ids))
    return one_to_one


def linked_target_instance_id(relationships_tsv: Path, related_instance_id: str, phase: str) -> str:
    if phase == "related":
        return related_instance_id
    if phase != "experience":
        raise ValueError(f"unknown linked task phase: {phase}")

    links: dict[str, set[str]] = defaultdict(set)
    with relationships_tsv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row.get("related_instance_id") == related_instance_id and row.get("experience_instance_id"):
                links[related_instance_id].add(row["experience_instance_id"])

    experience_ids = links.get(related_instance_id, set())
    if not experience_ids:
        raise ValueError(f"related instance has no experience link: {related_instance_id}")
    if len(experience_ids) > 1:
        raise ValueError(
            f"related instance has multiple experience tasks and is not supported yet: {related_instance_id}"
        )
    return next(iter(experience_ids))


def task_manifest_from_row(row: dict, owner: str) -> TaskManifest:
    problem_statement = row["problem_statement"]
    return TaskManifest(
        instance_id=row["instance_id"],
        repo=row["repo"],
        base_commit=row["base_commit"],
        problem_statement=problem_statement,
        issue_title=first_problem_statement_line(problem_statement),
        issue_body=problem_statement,
        target_owner=owner,
        target_repo=row["instance_id"],
    )


def build_linked_task_manifest(
    experience_jsonl: Path,
    related_jsonl: Path,
    relationships_tsv: Path,
    owner: str,
    related_instance_id: str,
    phase: str,
) -> TaskManifest:
    target_id = linked_target_instance_id(relationships_tsv, related_instance_id, phase)
    source_path = experience_jsonl if phase == "experience" else related_jsonl
    tasks = read_jsonl_tasks(source_path)
    if target_id not in tasks:
        raise ValueError(f"{phase} target not found in {source_path}: {target_id}")
    return task_manifest_from_row(tasks[target_id], owner)
