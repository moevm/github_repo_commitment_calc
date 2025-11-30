from dataclasses import dataclass


@dataclass(kw_only=True, frozen=True)
class PullRequestData:
    repository_name: str = ''
    title: str = ''
    id: int = 0
    state: str = ''
    commit_into: str = ''
    commit_from: str = ''
    created_at: str = ''
    creator_name: str = ''
    creator_login: str = ''
    creator_email: str = ''
    changed_files: str = ''
    comment_body: str = ''
    comment_created_at: str = ''
    comment_author_name: str = ''
    comment_author_login: str = ''
    comment_author_email: str = ''
    merger_name: str | None = None
    merger_login: str | None = None
    merger_email: str | None = None
    source_branch: str = ''
    target_branch: str = ''
    assignee_story: str = ''
    related_issues: str = ''
    labels: str = ''
    milestone: str = ''