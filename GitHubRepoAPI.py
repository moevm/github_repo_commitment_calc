from github import Github
from typing import Optional, List
import logging
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Модельные классы
@dataclass
class Repository:
    _id: str
    name: str
    url: str

@dataclass
class Contributor:
    username: str
    email: str

@dataclass
class Commit:
    _id: str
    message: str
    author: Contributor
    date: datetime

@dataclass
class Issue:
    _id: int
    title: str
    author: Contributor
    state: str

@dataclass
class PullRequest:
    _id: int
    title: str
    author: Contributor
    state: str

@dataclass
class WikiPage:
    title: str
    content: str

@dataclass
class Branch:
    name: str
    last_commit: Commit | None

# Интерфейс API
class IRepositoryAPI(ABC):
    @abstractmethod
    def get_repository(self, id: str) -> Repository | None:
        """Получить репозиторий по его идентификатору."""
        pass

    @abstractmethod
    def get_commits(self, repo: Repository) -> list[Commit]:
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
    def get_wiki_pages(self, repo: Repository) -> list[WikiPage]:
        """Получить список wiki-страниц для репозитория."""
        pass


class GitHubRepoAPI(IRepositoryAPI):
    
    def __init__(self, client):
        self.client = client

    def get_repository(self, id: str) -> Optional[Repository]:
        try:
            repo = self.client.get_repo(id)
            return Repository(repo.full_name, repo.name, repo.html_url)
        except Exception as e:
            logging.error(f"Failed to get repository {id} from GitHub: {e}")
            return None

    def get_commits(self, repo: Repository) -> List[Commit]:
        try:
            commits = self.client.get_repo(repo.id).get_commits()
            return [
                Commit(
                    c.sha,
                    c.commit.message,
                    Contributor(c.author.login if c.author else "unknown", c.commit.author.email),
                    c.commit.author.date
                ) for c in commits
            ]
        except Exception as e:
            logging.error(f"Failed to get commits from GitHub for repo {repo.name}: {e}")
            return []

    def get_contributors(self, repo: Repository) -> List[Contributor]:
        try:
            contributors = self.client.get_repo(repo.id).get_contributors()
            return [Contributor(c.login, c.email or "") for c in contributors]
        except Exception as e:
            logging.error(f"Failed to get contributors from GitHub for repo {repo.name}: {e}")
            return []

    def get_issues(self, repo: Repository) -> List[Issue]:
        try:
            issues = self.client.get_repo(repo.id).get_issues(state='all')
            return [
                Issue(
                    i.number,
                    i.title,
                    Contributor(i.user.login, i.user.email or ""),
                    i.state
                ) for i in issues
            ]
        except Exception as e:
            logging.error(f"Failed to get issues from GitHub for repo {repo.name}: {e}")
            return []
        

    def get_pull_requests(self, repo: Repository) -> List[PullRequest]:
        try:
            pulls = self.client.get_repo(repo.id).get_pulls(state='all')
            return [
                PullRequest(
                    p.number,
                    p.title,
                    Contributor(p.user.login, p.user.email or ""),
                    p.state
                ) for p in pulls
            ]
        except Exception as e:
            logging.error(f"Failed to get pull requests from GitHub for repo {repo.name}: {e}")
            return []
        

# Точка входа для тестирования
if __name__ == "__main__":
    #клиент GitHub (используйте ваш токен)
    client = Github("tocken")
    api = GitHubRepoAPI(client)

    # Укажите ваш репозиторий 
    repo_name = "ваш_username/ваш_repo"

    # Получение репозитория
    repo = api.get_repository(repo_name)
    if not repo:
        print("Repository not found.")
        exit()

    # Вывод информации о репозитории
    print(f"Repository: {repo.name}, URL: {repo.url}")

    # Получение коммитов
    commits = api.get_commits(repo)
    print(f"Total commits: {len(commits)}")
    for commit in commits[:10]:  # Выведем первые 10 коммитов
        print(f"Commit: {commit._id}, Message: {commit.message}, Author: {commit.author.username}")

    # Получение контрибьюторов
    contributors = api.get_contributors(repo)
    print(f"Total contributors: {len(contributors)}")
    for contributor in contributors:
        print(f"Contributor: {contributor.username}, Email: {contributor.email}")

    # Получение issues
    issues = api.get_issues(repo)
    print(f"Total issues: {len(issues)}")
    for issue in issues[:10]:  # Выведем первые 10 issues
        print(f"Issue: {issue._id}, Title: {issue.title}, State: {issue.state}")

    # Получение pull requests
    pulls = api.get_pull_requests(repo)
    print(f"Total pull requests: {len(pulls)}")
    for pull in pulls[:10]:  # Выведем первые 10 pull requests
        print(f"Pull Request: {pull._id}, Title: {pull.title}, State: {pull.state}")