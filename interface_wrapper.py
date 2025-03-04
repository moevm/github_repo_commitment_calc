from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Модельные классы
class Repository:
    def __init__(self, id: str, name: str, url: str):
        self.id = id
        self.name = name
        self.url = url

    def __repr__(self):
        return f"Repository(id={self.id}, name={self.name}, url={self.url})"

class Commit:
    def __init__(self, id: str, message: str, author: 'Contributor', date: datetime):
        self.id = id
        self.message = message
        self.author = author
        self.date = date

    def __repr__(self):
        return f"Commit(id={self.id}, message={self.message}, author={self.author}, date={self.date})"

class Contributor:
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email

    def __repr__(self):
        return f"Contributor(username={self.username}, email={self.email})"

class Issue:
    def __init__(self, id: str, title: str, author: Contributor, state: str):
        self.id = id
        self.title = title
        self.author = author
        self.state = state

    def __repr__(self):
        return f"Issue(id={self.id}, title={self.title}, author={self.author}, state={self.state})"

class PullRequest:
    def __init__(self, id: str, title: str, author: Contributor, state: str):
        self.id = id
        self.title = title
        self.author = author
        self.state = state

    def __repr__(self):
        return f"PullRequest(id={self.id}, title={self.title}, author={self.author}, state={self.state})"

class WikiPage:
    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content

    def __repr__(self):
        return f"WikiPage(title={self.title}, content={self.content[:50]}...)"  # Ограничиваем вывод content для удобства

# Интерфейс API
class IRepositoryAPI(ABC):
    @abstractmethod
    def get_repository(self, id: str) -> Optional[Repository]:
        """Получить репозиторий по его идентификатору."""
        pass

    @abstractmethod
    def get_commits(self, repo: Repository) -> List[Commit]:
        """Получить список коммитов для репозитория."""
        pass

    @abstractmethod
    def get_contributors(self, repo: Repository) -> List[Contributor]:
        """Получить список контрибьюторов для репозитория."""
        pass

    @abstractmethod
    def get_issues(self, repo: Repository) -> List[Issue]:
        """Получить список issues для репозитория."""
        pass

    @abstractmethod
    def get_pull_requests(self, repo: Repository) -> List[PullRequest]:
        """Получить список pull requests для репозитория."""
        pass

    @abstractmethod
    def get_wiki_pages(self, repo: Repository) -> List[WikiPage]:
        """Получить список wiki-страниц для репозитория."""
        pass

# Фабрика для создания API
class RepositoryFactory:
    @staticmethod
    def create_api(source: str, client) -> IRepositoryAPI:
        if client is None:
            raise ValueError("Client cannot be None")
        if source == 'github':
            return GitHubRepoAPI(client)
        elif source == 'forgejo':
            return ForgejoRepoAPI(client)
        else:
            raise ValueError(f"Unsupported source: {source}")

# Сервис для расчёта метрик
class CommitmentCalculator:
    def __init__(self, api: IRepositoryAPI):
        self.api = api

    def calculate(self, repo: Repository) -> Dict[str, int]:
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
