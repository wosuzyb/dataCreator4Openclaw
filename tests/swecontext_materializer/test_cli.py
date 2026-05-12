import json
from pathlib import Path

from tools.swecontext_materializer.cli import main


def test_prepare_manifest_command_writes_manifest(tmp_path: Path) -> None:
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "relationships.tsv"
    output = tmp_path / "manifest.jsonl"
    related.write_text(
        json.dumps(
            {
                "instance_id": "astropy__astropy-15082",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "problem_statement": "Title\nBody",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    relationships.write_text(
        "related_instance_id\trelated_pr_url\trelated_issue_url\texperience_instance_id\texperience_pr_url\texperience_issue_url\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "prepare-manifest",
            "--related-jsonl",
            str(related),
            "--relationships-tsv",
            str(relationships),
            "--owner",
            "wosuzyb",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["target_owner"] == "wosuzyb"


def test_status_command_prints_status(tmp_path: Path, capsys) -> None:
    status = tmp_path / "status.json"
    status.write_text('{"task-1": {"stage": "issue_created"}}', encoding="utf-8")

    exit_code = main(["status", "--status-file", str(status)])

    assert exit_code == 0
    assert "task-1" in capsys.readouterr().out


def test_activate_task_command_records_activation(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.jsonl"
    status = tmp_path / "status.json"
    manifest.write_text(
        json.dumps(
            {
                "instance_id": "astropy__astropy-15082",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "problem_statement": "Title\nBody",
                "issue_title": "Title",
                "issue_body": "Title\nBody",
                "target_owner": "wosuzyb",
                "target_repo": "astropy__astropy-15082",
                "related_pr_url": None,
                "related_issue_url": None,
                "experience_instance_ids": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    from tools.swecontext_materializer.models import ActivationResult

    def fake_activate_task(tasks, instance_id, cleanup_issues, cleanup_prs, dry_run):
        return ActivationResult(
            instance_id=instance_id,
            upstream_repo="astropy/astropy",
            active_repo="wosuzyb/astropy-15082",
            base_commit="abc123",
            issue_number=4,
            closed_issues=[1],
            closed_prs=[],
        )

    monkeypatch.setattr("tools.swecontext_materializer.cli.activate_task", fake_activate_task)

    exit_code = main(
        [
            "activate-task",
            "--manifest",
            str(manifest),
            "--status-file",
            str(status),
            "--instance-id",
            "astropy__astropy-15082",
        ]
    )

    assert exit_code == 0
    data = json.loads(status.read_text(encoding="utf-8"))
    assert data["astropy__astropy-15082"]["stage"] == "task_activated"
    assert data["astropy__astropy-15082"]["active_repo"] == "wosuzyb/astropy-15082"
    assert data["astropy__astropy-15082"]["issue_number"] == 4


def test_activate_linked_task_command_records_linked_phase(tmp_path: Path, monkeypatch) -> None:
    experience = tmp_path / "experience.jsonl"
    related = tmp_path / "related.jsonl"
    relationships = tmp_path / "relationships.tsv"
    status = tmp_path / "status.json"
    experience.write_text("", encoding="utf-8")
    related.write_text("", encoding="utf-8")
    relationships.write_text("", encoding="utf-8")

    from tools.swecontext_materializer.models import ActivationResult, TaskManifest

    def fake_build_linked_task_manifest(
        experience_jsonl,
        related_jsonl,
        relationships_tsv,
        owner,
        related_instance_id,
        phase,
    ):
        return TaskManifest(
            instance_id="astropy__astropy-14995",
            repo="astropy/astropy",
            base_commit="exp-base",
            problem_statement="Experience title\nBody",
            issue_title="Experience title",
            issue_body="Experience title\nBody",
            target_owner=owner,
            target_repo="astropy__astropy-14995",
        )

    def fake_activate_task(tasks, instance_id, cleanup_issues, cleanup_prs, dry_run):
        return ActivationResult(
            instance_id=instance_id,
            upstream_repo="astropy/astropy",
            active_repo="wosuzyb/astropy-14995",
            base_commit="exp-base",
            issue_number=9,
        )

    monkeypatch.setattr("tools.swecontext_materializer.cli.build_linked_task_manifest", fake_build_linked_task_manifest)
    monkeypatch.setattr("tools.swecontext_materializer.cli.activate_task", fake_activate_task)

    exit_code = main(
        [
            "activate-linked-task",
            "--experience-jsonl",
            str(experience),
            "--related-jsonl",
            str(related),
            "--relationships-tsv",
            str(relationships),
            "--status-file",
            str(status),
            "--owner",
            "wosuzyb",
            "--related-instance-id",
            "astropy__astropy-15082",
            "--phase",
            "experience",
        ]
    )

    assert exit_code == 0
    data = json.loads(status.read_text(encoding="utf-8"))
    entry = data["astropy__astropy-14995"]
    assert entry["stage"] == "task_activated"
    assert entry["linked_related_instance_id"] == "astropy__astropy-15082"
    assert entry["linked_phase"] == "experience"
    assert entry["linked_target_instance_id"] == "astropy__astropy-14995"
