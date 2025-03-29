from interface_wrapper import (
    Branch,
    Comment,
    Commit,
    Contributor,
    Invite,
    IRepositoryAPI,
    Issue,
    PullRequest,
    Repository,
    User,
    WikiPage,
    logging,
)

from github import Github, GithubException


class GitHubRepoAPI(IRepositoryAPI):
    def __init__(self, client: Github):
        self.client = self._client_validation(client)

    @staticmethod
    def _client_validation(client: Github) -> Github:
        try:
            client.get_user().login
        except GithubException as err:
            logging.error(f'Github: Connect: error {err.data}')
            logging.error(
                'Github: Connect: user could not be authenticated please try again.'
            )
            exit(1)
        else:
            return client

    def get_user_data(self, user) -> User:
        return User(
            login=user.login,
            username=user.name,
            email=user.email,
            html_url=user.html_url,
            node_id=user.node_id,
            type=user.type,
            bio=user.bio,
            site_admin=user.site_admin,
            _id=user.id,
        )

    def get_repository(self, id: str) -> Repository | None:
        try:
            repo = self.client.get_repo(id)
            return Repository(
                _id=repo.full_name,
                name=repo.name,
                url=repo.html_url,
                default_branch=Branch(name=repo.default_branch, last_commit=None),
                owner=self.get_user_data(repo.owner),
            )
        except Exception as e:
            logging.error(f"Failed to get repository {id} from GitHub: {e}")
            return None

    def get_collaborator_permission(self, repo: Repository, user: User) -> str:
        return self.client.get_repo(repo._id).get_collaborator_permission(user.login)

    def get_commits(self, repo: Repository, files: bool = True) -> list[Commit]:
        try:
            commits = self.client.get_repo(repo._id).get_commits()
            return [
                Commit(
                    _id=c.sha,
                    message=c.commit.message,
                    author=self.get_user_data(c.author),
                    date=c.commit.author.date,
                    files=[f.filename for f in c.files] if files else None,
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
                    closed_by=self.get_user_data(i.closed_by) if i.closed_by else None,
                    body=i.body,
                    user=self.get_user_data(i.user),
                    labels=[label.name for label in i.labels],
                    milestone=i.milestone.title if i.milestone else None,
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
                    author=self.get_user_data(p.user),
                    state=p.state,
                    created_at=p.created_at,
                    head_label=p.head.label,
                    base_label=p.base.label,
                    head_ref=p.head.ref,
                    base_ref=p.base.ref,
                    merged_by=self.get_user_data(p.merged_by) if p.merged_by else None,
                    files=[file.filename for file in p.get_files()],
                    issue_url=p.issue_url,
                    labels=[label.name for label in p.labels],
                    milestone=p.milestone.title if p.milestone else None,
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
            result.append(
                Repository(_id=repo.full_name, name=repo.name, url=repo.html_url)
            )
        return result

    def get_comments(self, repo, obj) -> list[Comment]:
        result = []
        if isinstance(obj, Issue):
            # TODO оптимизировать
            issues = self.client.get_repo(repo._id).get_issues(state='all')
            issue = None
            for i in issues:
                if i.number == obj._id:
                    issue = i
                    break
            for c in issue.get_comments():
                result.append(
                    Comment(
                        body=c.body,
                        created_at=c.created_at,
                        author=self.get_user_data(c.user),
                    )
                )
        elif isinstance(obj, PullRequest):
            # TODO оптимизировать
            pulls = self.client.get_repo(repo._id).get_pulls(state='all')
            pull = None
            for p in pulls:
                if p.number == obj._id:
                    pull = p
                    break
            for c in pull.get_comments():
                result.append(
                    Comment(
                        body=c.body,
                        created_at=c.created_at,
                        author=self.get_user_data(c.user.login),
                    )
                )

        return result

    def get_invites(self, repo: Repository) -> list[Invite]:
        try:
            invites = self.client.get_repo(repo._id).get_pending_invitations()
            return [
                Invite(
                    _id=i._id,
                    invitee=self.get_user_data(i.invitee),
                    created_at=i.created_at,
                    html_url=i.html_url,
                )
                for i in invites
            ]
        except Exception as e:
            logging.error(
                f"Failed to get invites from GitHub for repo {repo.name}: {e}"
            )
            return []

    def get_rate_limiting(self) -> tuple[int, int]:
        return self.client.rate_limiting


# Точка входа для тестирования
if __name__ == "__main__":
    # Создайте клиент GitHub (используйте ваш токен)
    # client = Github("tocken")
    api = GitHubRepoAPI('client')

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
