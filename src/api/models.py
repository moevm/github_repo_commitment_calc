import logging
from dataclasses import dataclass
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Модельные классы
@dataclass
class Contributor:
    username: str
    email: str


@dataclass
class User:
    _id: int
    login: str
    username: str
    email: str
    html_url: str
    node_id: str
    type: str
    bio: str
    site_admin: bool


@dataclass
class Commit:
    _id: str
    message: str
    author: User
    date: datetime
    files: list[str]
    additions: int
    deletions: int


@dataclass
class Branch:
    name: str
    last_commit: Commit | None


@dataclass
class Repository:
    _id: str
    name: str
    url: str
    default_branch: Branch
    owner: User


@dataclass
class Issue:
    _id: int
    number: int
    title: str
    state: str
    created_at: datetime
    closed_at: datetime
    body: str
    user: User
    closed_by: User
    labels: list[str]
    milestone: str


@dataclass
class PullRequest:
    _id: int
    title: str
    author: User
    state: str
    created_at: datetime
    head_label: str
    base_label: str
    head_ref: str
    base_ref: str
    merged_by: User
    merged: bool
    files: list[str]
    issue_url: str
    labels: list[str]
    milestone: str
    comments: int = 0
    review_comments: int = 0
    repository_name: str = ""


@dataclass
class Invite:
    _id: int
    invitee: User
    created_at: datetime | None
    html_url: str


@dataclass
class Comment:
    body: str
    created_at: datetime
    author: User


@dataclass
class WikiPage:
    title: str
    content: str


@dataclass
class WorkflowRun:
    display_title: str
    event: str
    head_branch: str
    head_sha: str
    name: str
    path: str
    created_at: datetime
    run_started_at: datetime
    updated_at: datetime
    conclusion: str
    status: str
    url: str
