import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from github import Auth, Github
from pyforgejo import PyforgejoApi

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
    _id: str
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
    files: list[str]
    issue_url: str
    labels: list[str]
    milestone: str


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


# Интерфейс API
class IRepositoryAPI(ABC):

    @abstractmethod
    def get_user_data(self, user) -> User:
        pass

    @abstractmethod
    def get_repository(self, id: str) -> Repository | None:
        """Получить репозиторий по его идентификатору."""
        pass

    @abstractmethod
    def get_collaborator_permission(self, repo: Repository, user: User) -> str:
        pass

    @abstractmethod
    def get_commits(self, repo: Repository, files: bool = True) -> list[Commit]:
        """Получить список коммитов для репозитория."""
        pass

    @abstractmethod
    def get_contributors(self, repo: Repository) -> list[Contributor]:
        """Получить список контрибьюторов для репозитория."""
        pass

    @abstractmethod
    def get_issues(self, repo: Repository) -> list[Issue]:
        """Получить список issues для репозитория."""
        pass

    @abstractmethod
    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
        """Получить список pull requests для репозитория."""
        pass

    @abstractmethod
    def get_branches(self, repo: Repository) -> list[Branch]:
        """Получить список веток для репозитория."""
        pass

    @abstractmethod
    def get_forks(self, repo: Repository) -> list[Repository]:
        pass

    @abstractmethod
    def get_wiki_pages(self, repo: Repository) -> list[WikiPage]:
        """Получить список wiki-страниц для репозитория."""
        pass

    @abstractmethod
    def get_comments(self, obj) -> list[Comment]:
        pass

    @abstractmethod
    def get_invites(self, repo: Repository) -> list[Invite]:
        pass

    @abstractmethod
    def get_rate_limiting(self) -> tuple[int, int]:
        pass

    @abstractmethod
    def get_workflow_runs(self, repo: Repository) -> list[WorkflowRun]:
        pass


class RepositoryFactory:
    @staticmethod
    def create_api(token: str, base_url: str | None = None) -> IRepositoryAPI:
        from ForgejoRepoAPI import ForgejoRepoAPI
        from GitHubRepoAPI import GitHubRepoAPI

        errors = []

        try:
            return GitHubRepoAPI(Github(auth=Auth.Token(token)))
        except Exception as e:
            errors.append(f"GitHub login failed: {e}")

        if base_url:
            try:
                return ForgejoRepoAPI(PyforgejoApi(api_key=token, base_url=base_url))
            except Exception as e:
                errors.append(f"Forgejo login failed: {e}")

        raise Exception(" / ".join(errors))


# Сервис для расчёта метрик
class CommitmentCalculator:
    def __init__(self, api: IRepositoryAPI):
        self.api = api

    def calculate(self, repo: Repository) -> dict[str, int]:
        if not repo:
            return {}
        try:
            commits = self.api.get_commits(repo)
            if not commits:
                return {}
            result = {}
            for commit in commits:
                author = commit.author.username
                result[author] = result.get(author, 0) + 1
            return result
        except Exception as e:
            logging.error(f"Failed to calculate commitment for repo {repo.name}: {e}")
            return {}
