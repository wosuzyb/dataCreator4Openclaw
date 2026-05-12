from tools.swecontext_materializer.models import TaskManifest
from tools.swecontext_materializer.naming import active_repo_name, task_number


def make_task(instance_id: str, repo: str) -> TaskManifest:
    return TaskManifest(
        instance_id=instance_id,
        repo=repo,
        base_commit="abc123",
        problem_statement="Title\nBody",
        issue_title="Title",
        issue_body="Title\nBody",
        target_owner="wosuzyb",
        target_repo=instance_id,
    )


def test_task_number_uses_suffix_after_last_dash() -> None:
    assert task_number("astropy__astropy-15082") == "15082"
    assert task_number("scikit-learn__scikit-learn-25365") == "25365"


def test_active_repo_name_uses_upstream_repo_name_and_task_number() -> None:
    assert active_repo_name(make_task("astropy__astropy-15082", "astropy/astropy")) == "astropy-15082"
    assert active_repo_name(make_task("django__django-30153", "django/django")) == "django-30153"
    assert (
        active_repo_name(make_task("scikit-learn__scikit-learn-25365", "scikit-learn/scikit-learn"))
        == "scikit-learn-25365"
    )
