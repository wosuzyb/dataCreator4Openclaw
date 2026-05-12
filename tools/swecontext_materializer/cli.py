from __future__ import annotations

import argparse
import json
from pathlib import Path

from .active_repo import activate_task
from .git_ops import prepare_task_checkout, push_task_checkout
from .github_ops import create_issue, create_repo
from .linked_tasks import build_linked_task_manifest
from .manifest import build_manifest, read_manifest_jsonl, write_manifest_jsonl
from .status import StatusStore


DEFAULT_WORKDIR = Path("generated/swecontextbench-lite")
DEFAULT_MANIFEST = DEFAULT_WORKDIR / "manifest.jsonl"
DEFAULT_STATUS = DEFAULT_WORKDIR / "status.json"
DEFAULT_EXPERIENCE_JSONL = Path("SWEContextBench/lite/experience.jsonl")
DEFAULT_RELATED_JSONL = Path("SWEContextBench/lite/related.jsonl")
DEFAULT_RELATIONSHIPS_TSV = Path("SWEContextBench/lite/related_relationship_links.tsv")


def add_common_execution_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)


def selected_tasks(manifest_path: Path, limit: int | None):
    tasks = read_manifest_jsonl(manifest_path)
    return tasks if limit is None else tasks[:limit]


def cmd_prepare_manifest(args: argparse.Namespace) -> int:
    tasks = build_manifest(args.related_jsonl, args.relationships_tsv, args.owner)
    write_manifest_jsonl(tasks, args.output)
    print(f"planned_tasks={len(tasks)}")
    print(f"output={args.output}")
    return 0


def cmd_clone_checkout(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            prepare_task_checkout(args.workdir, task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "source_checkout_prepared")
            stage = "source_checkout_dry_run" if args.dry_run else "source_checkout_prepared"
            print(f"{task.instance_id}: {stage}")
        except Exception as exc:
            status.fail(task.instance_id, "source_checkout_failed", str(exc))
            print(f"{task.instance_id}: source_checkout_failed: {exc}")
    return 0


def cmd_create_repos(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            result = create_repo(task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "repo_created")
            print(f"{task.instance_id}: repo_{result}")
        except Exception as exc:
            status.fail(task.instance_id, "repo_create_failed", str(exc))
            print(f"{task.instance_id}: repo_create_failed: {exc}")
    return 0


def cmd_push_repos(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            push_task_checkout(args.workdir, task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "code_pushed")
            stage = "push_dry_run" if args.dry_run else "code_pushed"
            print(f"{task.instance_id}: {stage}")
        except Exception as exc:
            status.fail(task.instance_id, "push_failed", str(exc))
            print(f"{task.instance_id}: push_failed: {exc}")
    return 0


def cmd_create_issues(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    for task in selected_tasks(args.manifest, args.limit):
        try:
            create_issue(task, dry_run=args.dry_run)
            if not args.dry_run:
                status.mark(task.instance_id, "issue_created")
            stage = "issue_dry_run" if args.dry_run else "issue_created"
            print(f"{task.instance_id}: {stage}")
        except Exception as exc:
            status.fail(task.instance_id, "issue_create_failed", str(exc))
            print(f"{task.instance_id}: issue_create_failed: {exc}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    print(json.dumps(status.all(), indent=2, sort_keys=True))
    return 0


def cmd_activate_task(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    tasks = read_manifest_jsonl(args.manifest)
    try:
        result = activate_task(
            tasks,
            args.instance_id,
            cleanup_issues=args.cleanup_issues,
            cleanup_prs=args.cleanup_prs,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            status.record_activation(
                result.instance_id,
                {
                    "upstream_repo": result.upstream_repo,
                    "active_repo": result.active_repo,
                    "base_commit": result.base_commit,
                    "issue_number": result.issue_number,
                    "closed_issues": result.closed_issues,
                    "deleted_issues": result.deleted_issues,
                    "closed_prs": result.closed_prs,
                    "deleted_branches": result.deleted_branches,
                    "deleted_tags": result.deleted_tags,
                    "cleanup_issues": args.cleanup_issues,
                    "cleanup_prs": args.cleanup_prs,
                },
            )
        print(f"{result.instance_id}: activated {result.active_repo} issue={result.issue_number}")
        return 0
    except Exception as exc:
        status.fail(args.instance_id, "activate_failed", str(exc))
        print(f"{args.instance_id}: activate_failed: {exc}")
        return 1


def cmd_activate_linked_task(args: argparse.Namespace) -> int:
    status = StatusStore(args.status_file)
    try:
        task = build_linked_task_manifest(
            args.experience_jsonl,
            args.related_jsonl,
            args.relationships_tsv,
            args.owner,
            args.related_instance_id,
            args.phase,
        )
        result = activate_task(
            [task],
            task.instance_id,
            cleanup_issues=args.cleanup_issues,
            cleanup_prs=args.cleanup_prs,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            status.record_activation(
                result.instance_id,
                {
                    "upstream_repo": result.upstream_repo,
                    "active_repo": result.active_repo,
                    "base_commit": result.base_commit,
                    "issue_number": result.issue_number,
                    "closed_issues": result.closed_issues,
                    "deleted_issues": result.deleted_issues,
                    "closed_prs": result.closed_prs,
                    "deleted_branches": result.deleted_branches,
                    "deleted_tags": result.deleted_tags,
                    "cleanup_issues": args.cleanup_issues,
                    "cleanup_prs": args.cleanup_prs,
                    "linked_related_instance_id": args.related_instance_id,
                    "linked_phase": args.phase,
                    "linked_target_instance_id": result.instance_id,
                },
            )
        print(
            f"{args.related_instance_id}: {args.phase} activated "
            f"{result.instance_id} {result.active_repo} issue={result.issue_number}"
        )
        return 0
    except Exception as exc:
        status.fail(args.related_instance_id, "activate_linked_failed", str(exc))
        print(f"{args.related_instance_id}: activate_linked_failed: {exc}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swecontext-materializer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-manifest")
    prepare.add_argument("--related-jsonl", type=Path, default=Path("SWEContextBench/lite/related.jsonl"))
    prepare.add_argument(
        "--relationships-tsv",
        type=Path,
        default=Path("SWEContextBench/lite/related_relationship_links.tsv"),
    )
    prepare.add_argument("--owner", default="wosuzyb")
    prepare.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)
    prepare.set_defaults(func=cmd_prepare_manifest)

    for name, func in [
        ("clone-checkout", cmd_clone_checkout),
        ("create-repos", cmd_create_repos),
        ("push-repos", cmd_push_repos),
        ("create-issues", cmd_create_issues),
    ]:
        command = subparsers.add_parser(name)
        add_common_execution_args(command)
        command.set_defaults(func=func)

    status = subparsers.add_parser("status")
    status.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    status.set_defaults(func=cmd_status)

    activate = subparsers.add_parser("activate-task")
    activate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    activate.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    activate.add_argument("--instance-id", required=True)
    activate.add_argument("--cleanup-issues", choices=["none", "delete"], default="delete")
    activate.add_argument(
        "--cleanup-prs",
        choices=["none", "close", "close-and-delete-branches"],
        default="close-and-delete-branches",
    )
    activate.add_argument("--dry-run", action="store_true")
    activate.set_defaults(func=cmd_activate_task)

    linked = subparsers.add_parser("activate-linked-task")
    linked.add_argument("--experience-jsonl", type=Path, default=DEFAULT_EXPERIENCE_JSONL)
    linked.add_argument("--related-jsonl", type=Path, default=DEFAULT_RELATED_JSONL)
    linked.add_argument("--relationships-tsv", type=Path, default=DEFAULT_RELATIONSHIPS_TSV)
    linked.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    linked.add_argument("--owner", default="wosuzyb")
    linked.add_argument("--related-instance-id", required=True)
    linked.add_argument("--phase", choices=["experience", "related"], required=True)
    linked.add_argument("--cleanup-issues", choices=["none", "delete"], default="delete")
    linked.add_argument(
        "--cleanup-prs",
        choices=["none", "close", "close-and-delete-branches"],
        default="close-and-delete-branches",
    )
    linked.add_argument("--dry-run", action="store_true")
    linked.set_defaults(func=cmd_activate_linked_task)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
