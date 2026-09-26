from abc import ABC, abstractmethod

from github import Auth, Github
from pyforgejo import PyforgejoApi

from src.api.models import (Branch, Comment, Commit, Contributor, Invite,
                            Issue, PullRequest, Repository, User, WikiPage,
                            WorkflowRun)


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

    @abstractmethod
    def get_base_url(self) -> str:
        pass


class RepositoryFactory:
    @staticmethod
    def create_api(token: str, base_url: str | None = None) -> IRepositoryAPI:
        from src.api.forgejo.ForgejoRepoAPI import ForgejoRepoAPI
        from src.api.github.GitHubRepoAPI import GitHubRepoAPI

        errors = []

        try:
            client = GitHubRepoAPI(Github(auth=Auth.Token(token)))
            if client.client:
                return client
        except Exception as e:
            errors.append(f"GitHub login failed: {e}")

        if base_url:
            try:
                return ForgejoRepoAPI(PyforgejoApi(api_key=token, base_url=base_url))
            except Exception as e:
                errors.append(f"Forgejo login failed: {e}")

        raise Exception(" / ".join(errors))
