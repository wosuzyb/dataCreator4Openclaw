import json
from pathlib import Path

import pytest

from tools.swecontext_materializer.linked_tasks import (
    build_linked_task_manifest,
    linked_target_instance_id,
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def task_row(instance_id: str, repo: str = "astropy/astropy", base_commit: str = "abc123") -> dict:
    return {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": base_commit,
        "problem_statement": f"{instance_id} title\nbody",
    }


def test_linked_target_instance_id_returns_experience_for_experience_phase(tmp_path: Path) -> None:
    relationships = tmp_path / "relationships.tsv"
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "astropy__astropy-15082\tpr\tissue\tastropy__astropy-14995\texp-pr\texp-issue\n",
        encoding="utf-8",
    )

    assert (
        linked_target_instance_id(relationships, "astropy__astropy-15082", "experience")
        == "astropy__astropy-14995"
    )


def test_linked_target_instance_id_returns_related_for_related_phase(tmp_path: Path) -> None:
    relationships = tmp_path / "relationships.tsv"
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "astropy__astropy-15082\tpr\tissue\tastropy__astropy-14995\texp-pr\texp-issue\n",
        encoding="utf-8",
    )

    assert linked_target_instance_id(relationships, "astropy__astropy-15082", "related") == "astropy__astropy-15082"


def test_linked_target_instance_id_rejects_multi_experience_links(tmp_path: Path) -> None:
    relationships = tmp_path / "relationships.tsv"
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "django__django-27910\tpr\tissue\tdjango__django-11742\texp-pr\texp-issue\n"
        "django__django-27910\tpr\tissue\tdjango__django-12125\texp-pr\texp-issue\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple experience tasks"):
        linked_target_instance_id(relationships, "django__django-27910", "experience")


def test_build_linked_task_manifest_uses_experience_jsonl_for_experience_phase(tmp_path: Path) -> None:
    experience = tmp_path / "experience.jsonl"
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "relationships.tsv"
    write_jsonl(experience, [task_row("astropy__astropy-14995", base_commit="exp-base")])
    write_jsonl(related, [task_row("astropy__astropy-15082", base_commit="rel-base")])
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "astropy__astropy-15082\thttps://github.com/astropy/astropy/pull/15082\tissue\tastropy__astropy-14995\texp-pr\texp-issue\n",
        encoding="utf-8",
    )

    task = build_linked_task_manifest(
        experience,
        related,
        relationships,
        owner="wosuzyb",
        related_instance_id="astropy__astropy-15082",
        phase="experience",
    )

    assert task.instance_id == "astropy__astropy-14995"
    assert task.base_commit == "exp-base"
    assert task.target_owner == "wosuzyb"
    assert task.target_repo == "astropy__astropy-14995"


def test_build_linked_task_manifest_uses_related_jsonl_for_related_phase(tmp_path: Path) -> None:
    experience = tmp_path / "experience.jsonl"
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "relationships.tsv"
    write_jsonl(experience, [task_row("astropy__astropy-14995", base_commit="exp-base")])
    write_jsonl(related, [task_row("astropy__astropy-15082", base_commit="rel-base")])
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "astropy__astropy-15082\thttps://github.com/astropy/astropy/pull/15082\tissue\tastropy__astropy-14995\texp-pr\texp-issue\n",
        encoding="utf-8",
    )

    task = build_linked_task_manifest(
        experience,
        related,
        relationships,
        owner="wosuzyb",
        related_instance_id="astropy__astropy-15082",
        phase="related",
    )

    assert task.instance_id == "astropy__astropy-15082"
    assert task.base_commit == "rel-base"
    assert task.target_repo == "astropy__astropy-15082"
