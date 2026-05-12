import json
from pathlib import Path

from tools.swecontext_materializer.manifest import (
    build_manifest,
    first_problem_statement_line,
    read_manifest_jsonl,
    write_manifest_jsonl,
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_first_problem_statement_line_skips_blank_lines() -> None:
    assert first_problem_statement_line("\n\nBug title\n\nBody") == "Bug title"


def test_build_manifest_deduplicates_relationship_rows(tmp_path: Path) -> None:
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "related_relationship_links.tsv"
    write_jsonl(
        related,
        [
            {
                "instance_id": "astropy__astropy-15082",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "problem_statement": "Title line\n\nFull body",
            }
        ],
    )
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "astropy__astropy-15082\thttps://github.com/astropy/astropy/pull/15082\thttps://github.com/astropy/astropy/issues/15082\texp1\tpr\tissue\n"
        "astropy__astropy-15082\thttps://github.com/astropy/astropy/pull/15082\thttps://github.com/astropy/astropy/issues/15082\texp2\tpr\tissue\n",
        encoding="utf-8",
    )

    manifest = build_manifest(related, relationships, owner="wosuzyb")

    assert len(manifest) == 1
    task = manifest[0]
    assert task.instance_id == "astropy__astropy-15082"
    assert task.target_owner == "wosuzyb"
    assert task.target_repo == "astropy__astropy-15082"
    assert task.issue_title == "Title line"
    assert task.issue_body == "Title line\n\nFull body"
    assert task.related_issue_url == "https://github.com/astropy/astropy/issues/15082"
    assert task.related_pr_url == "https://github.com/astropy/astropy/pull/15082"
    assert task.experience_instance_ids == ["exp1", "exp2"]


def test_manifest_jsonl_round_trip(tmp_path: Path) -> None:
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "related_relationship_links.tsv"
    output = tmp_path / "manifest.jsonl"
    write_jsonl(
        related,
        [
            {
                "instance_id": "django__django-30153",
                "repo": "django/django",
                "base_commit": "def456",
                "problem_statement": "Ticket title\nbody",
            }
        ],
    )
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n"
        "django__django-30153\thttps://github.com/django/django/pull/10939\thttps://code.djangoproject.com/ticket/30153\texp3\tpr\tissue\n",
        encoding="utf-8",
    )

    write_manifest_jsonl(build_manifest(related, relationships, "wosuzyb"), output)

    loaded = read_manifest_jsonl(output)
    assert len(loaded) == 1
    assert loaded[0].repo == "django/django"
    assert loaded[0].base_commit == "def456"
