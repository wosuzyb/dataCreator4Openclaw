from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TaskManifest:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    issue_title: str
    issue_body: str
    target_owner: str
    target_repo: str
    related_pr_url: str | None = None
    related_issue_url: str | None = None
    experience_instance_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskManifest":
        return cls(**data)


@dataclass(frozen=True)
class ActivationResult:
    instance_id: str
    upstream_repo: str
    active_repo: str
    base_commit: str
    issue_number: int | None
    closed_issues: list[int] = field(default_factory=list)
    deleted_issues: list[int] = field(default_factory=list)
    closed_prs: list[int] = field(default_factory=list)
    deleted_branches: list[str] = field(default_factory=list)
