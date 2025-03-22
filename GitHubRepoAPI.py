from interface_wrapper import (
    logging,
    Repository,
    Contributor,
    Commit,
    Issue,
    PullRequest,
    WikiPage,
    Branch,
    IRepositoryAPI,
    User,
    Comment
)
from github import Github


class GitHubRepoAPI(IRepositoryAPI):

    def __init__(self, client):
        self.client = Github(client)

    def get_repository(self, id: str) -> Repository | None:
        try:
            repo = self.client.get_repo(id)
            return Repository(_id=repo.full_name, name=repo.name, url=repo.html_url, default_branch=Branch(name=repo.default_branch, last_commit=None), owner=User(login=repo.owner.login,username=repo.owner.name,email=repo.owner.email))
        except Exception as e:
            logging.error(f"Failed to get repository {id} from GitHub: {e}")
            return None

    def get_commits(self, repo: Repository) -> list[Commit]:
        try:
            commits = self.client.get_repo(repo._id).get_commits()
            return [
                Commit(
                    _id=c.sha,
                    message=c.commit.message,
                    author=Contributor(
                        c.author.login if c.author else "unknown", c.commit.author.email
                    ),
                    date=c.commit.author.date,
                    files=[
                        f.filename
                            for f in c.files
                    ]
                )
                for c in commits
            ]
        except Exception as e:
            logging.error(
                f"Failed to get commits from GitHub for repo {repo.name}: {e}"
            )
            return []

    def get_contributors(self, repo: Repository) -> list[Contributor]:
        try:
            contributors = self.client.get_repo(repo._id).get_contributors()
            return [Contributor(c.login, c.email or "") for c in contributors]
        except Exception as e:
            logging.error(
                f"Failed to get contributors from GitHub for repo {repo.name}: {e}"
            )
            return []

    def get_issues(self, repo: Repository) -> list[Issue]:
        try:
            issues = self.client.get_repo(repo._id).get_issues(state='all')
            return [
                Issue(
                    _id=i.number,
                    title=i.title,
                    state=i.state,
                    created_at=i.created_at,
                    closed_at=i.closed_at,
                    closed_by=User(login=i.closed_by.login,username=i.closed_by.name,email=i.closed_by.email) if i.closed_by else None,
                    body=i.body,
                    user=User(login=i.user.login,username=i.user.name,email=i.user.email),
                    labels= [
                        l.name
                        for l in i.labels
                    ],
                    milestone=i.milestone.title if i.milestone else None
                )
                for i in issues
            ]
        except Exception as e:
            logging.error(f"Failed to get issues from GitHub for repo {repo.name}: {e}")
            return []

    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
        try:
            pulls = self.client.get_repo(repo._id).get_pulls(state='all')
            return [
                PullRequest(
                    _id=p.number,
                    title=p.title,
                    author=User(login=p.user.login, username=p.user.name, email=p.user.email),
                    state=p.state,
                    created_at=p.created_at,
                    head_label=p.head.label,
                    base_label=p.base.label,
                    head_ref=p.head.ref,
                    base_ref=p.base.ref,
                    merged_by=User(login=p.merged_by.login, username=p.merged_by.name, email=p.merged_by.email) if p.merged_by else None,
                    files=[
                        f.filename
                            for f in p.get_files()
                    ],
                    issue_url=p.issue_url,
                    labels= [
                        l.name
                        for l in p.labels
                    ],
                    milestone=p.milestone.title if p.milestone else None
                )
                for p in pulls
            ]
        except Exception as e:
            logging.error(
                f"Failed to get pull requests from GitHub for repo {repo.name}: {e}"
            )
            return []

    def get_branches(self, repo: Repository) -> list[Branch]:
        try:
            repo_client = self.client.get_repo(repo._id)
            branches = repo_client.get_branches()
            result = []

            for branch in branches:
                commit = repo_client.get_commit(branch.commit.sha)

                author = commit.author
                contributor = Contributor(
                    username=author.login if author else "unknown",
                    email=commit.commit.author.email or "",
                )

                commit_obj = Commit(
                    _id=commit.sha,
                    message=commit.commit.message,
                    author=contributor,
                    date=commit.commit.author.date,
                )

                result.append(Branch(name=branch.name, last_commit=commit_obj))

            return result

        except Exception as e:
            logging.error(
                f"Failed to get branches from GitHub for repo {repo.name}: {e}"
            )
            return []

    def get_wiki_pages(self, repo: Repository) -> list[WikiPage]:
        return

    def get_forks(self, repo: Repository) -> list[Repository]:
        repo_client = self.client.get_repo(repo._id)
        result = []
        for r in repo_client.get_forks():
            result.append(Repository(_id=repo.full_name, name=repo.name, url=repo.html_url))
        return result

    def get_comments(self, repo, obj) -> list[Comment]:
        result = []
        if type(obj) == Issue:
            # TODO оптимизировать
            issues = self.client.get_repo(repo._id).get_issues(state='all')
            issue = None
            for i in issues:
                if i.number == obj._id:
                    issue = i
                    break
            for c in issue.get_comments():
                result.append(Comment(body=c.body,created_at=c.created_at,author=User(login=c.user.login,username=c.user.name,email=c.user.email)))
        elif type(obj) == PullRequest:
            # TODO оптимизировать
            pulls = self.client.get_repo(repo._id).get_pulls(state='all')
            pull = None
            for p in pulls:
                if p.number == obj._id:
                    pull = p
                    break
            for c in pull.get_comments():
                result.append(Comment(body=c.body,created_at=c.created_at,author=User(login=c.user.login,username=c.user.name,email=c.user.email)))

        return result


# Точка входа для тестирования
if __name__ == "__main__":
    # Создайте клиент GitHub (используйте ваш токен)
    client = Github("tocken")
    api = GitHubRepoAPI(client)

    # Укажите ваш репозиторий
    repo_name = ""

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
        print(
            f"Commit: {commit._id}, Message: {commit.message}, Author: {commit.author.username}"
        )

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

    # Получение веток
    branches = api.get_branches(repo)
    print(f"Total branches: {len(branches)}")
    for branch in branches:
        print(
            f"Branch: {branch.name}, Last Commit: {branch.last_commit._id if branch.last_commit else 'None'}"
        )
