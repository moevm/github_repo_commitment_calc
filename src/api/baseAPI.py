from abc import ABC, abstractmethod

from github import Auth, Github
from pyforgejo import PyforgejoApi

from src.api.models import (
    Branch,
    Comment,
    Commit,
    Contributor,
    Invite,
    Issue,
    PullRequest,
    Repository,
    User,
    WikiPage,
    WorkflowRun,
)

import logging
import traceback

from src.api.utils import APITypes


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
    def create_api(api_type: APITypes, auth_data: dict) -> IRepositoryAPI:
        from src.api.forgejo.ForgejoRepoAPI import ForgejoRepoAPI
        from src.api.forgejo.ForgejoRepoDB import ForgejoDBClient, ForgejoRepoDB
        from src.api.github.GitHubRepoAPI import GitHubRepoAPI

        errors = []

        base_url = auth_data.get("base_url")
        token = auth_data.get("token")
        if auth_data.get("base_url") and api_type != APITypes.forgejo_db:
            api_type = APITypes.forgejo   # legacy code for backward compability

        match api_type:
            case APITypes.github:
                try:
                    client = GitHubRepoAPI(Github(auth=Auth.Token(token)))
                    if client.client:
                        return client, token
                except Exception as e:
                    errors.append(
                        f"GitHub login failed: {e}. Token: {str(token)[:4]}..."
                    )
            case APITypes.forgejo:
                try:
                    return ForgejoRepoAPI(
                        PyforgejoApi(api_key=token, base_url=base_url)
                    ), token
                except Exception as e:
                    errors.append(
                        f"Forgejo login failed: {e}. Base url: {base_url}. Token: {str(token)[:4]}..."
                    )
            case APITypes.forgejo_db:
                try:
                    token = auth_data.get("token")
                    return ForgejoRepoDB(ForgejoDBClient({'base_url': base_url, 'FORGEJO_DB_PASSWORD': token})), None
                except Exception as e:
                    errors.append(
                        f"Forgejo DB login failed: {e}. Base url: {base_url}. Token: {str(token)[:4]}..."
                    )

        if errors:
            logging.error(" / ".join(errors))
            logging.error("\n".join(traceback.format_stack()))

        return None, None
