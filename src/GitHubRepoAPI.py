from github import Github

from src.utils import (
    log_exceptions,
)
from src.interface_wrapper import (
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
    WorkflowRun,
)


class GitHubRepoAPI(IRepositoryAPI):
    def __init__(self, client: Github):
        self.client = self._client_validation(client)

    @staticmethod
    @log_exceptions(
        default_return=None,
        message="Github: Connect: user could not be authenticated. Please try again.",
        print_stacktrace=False,
    )
    def _client_validation(client: Github) -> Github | None:
        client.get_user().login
        return client

    def get_user_data(self, user) -> User:
        return User(
            login=user.login,
            username=user.name,
            email=user.email,  # always None
            html_url=user.html_url,
            node_id=user.node_id,
            type=user.type,
            bio=user.bio,
            site_admin=user.site_admin,
            _id=user.id,
        )

    def get_commit_data(self, commit, files=False) -> Commit:
        return Commit(
            _id=commit.sha,
            message=commit.commit.message,
            author=self.get_user_data(commit.author),
            date=commit.commit.author.date,
            files=[f.filename for f in commit.files] if files else None,
            additions=commit.stats.additions,
            deletions=commit.stats.deletions,
        )

    @log_exceptions(default_return=None, message="Failed to get repository from GitHub")
    def get_repository(self, id: str) -> Repository | None:
        repo = self.client.get_repo(id)
        return Repository(
            _id=repo.full_name,
            name=repo.name,
            url=repo.html_url,
            default_branch=Branch(name=repo.default_branch, last_commit=None),
            owner=self.get_user_data(repo.owner),
        )

    def get_collaborator_permission(self, repo: Repository, user: User) -> str:
        return self.client.get_repo(repo._id).get_collaborator_permission(user.login)

    @log_exceptions(default_return=[], message="Failed to get commits from GitHub")
    def get_commits(self, repo: Repository, files: bool = True) -> list[Commit]:
        commits = self.client.get_repo(repo._id).get_commits()
        return [self.get_commit_data(c, files) for c in commits]

    @log_exceptions(default_return=[], message="Failed to get contributors from GitHub")
    def get_contributors(self, repo: Repository) -> list[Contributor]:
        contributors = self.client.get_repo(repo._id).get_contributors()
        return [Contributor(c.login, c.email or "") for c in contributors]

    @log_exceptions(default_return=[], message="Failed to get issues from GitHub")
    def get_issues(self, repo: Repository) -> list[Issue]:
        issues = self.client.get_repo(repo._id).get_issues(state='all')
        return [
            Issue(
                _id=i.number,
                number=i.number,
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

    @log_exceptions(default_return=[], message="Failed to get pull requests from GitHub")
    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
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

    @log_exceptions(default_return=[], message="Failed to get branches from GitHub")
    def get_branches(self, repo: Repository) -> list[Branch]:
        repo_client = self.client.get_repo(repo._id)
        branches = repo_client.get_branches()
        result = []

        for branch in branches:
            commit = repo_client.get_commit(branch.commit.sha)
            commit_obj = self.get_commit_data(commit)
            result.append(Branch(name=branch.name, last_commit=commit_obj))

        return result

    def get_wiki_pages(self, repo: Repository) -> list[WikiPage]:
        raise Exception('not implemented')

    @log_exceptions(default_return=[], message="Failed to get forks from GitHub")
    def get_forks(self, repo: Repository) -> list[Repository]:
        repo_client = self.client.get_repo(repo._id)
        result = []

        for r in repo_client.get_forks():
            default_branch = Branch(name=r.default_branch, last_commit=None)
            owner = self.get_user_data(r.owner)

            result.append(
                Repository(
                    _id=r.full_name,
                    name=r.name,
                    url=r.html_url,
                    default_branch=default_branch,
                    owner=owner,
                )
            )

        return result

    @log_exceptions(default_return=[], message="Failed to get comments")
    def get_comments(self, repo, obj) -> list[Comment]:
        repo_client = self.client.get_repo(repo._id)

        if isinstance(obj, Issue):
            issue = repo_client.get_issue(number=obj._id)
            comments = issue.get_comments()
        elif isinstance(obj, PullRequest):
            pull = repo_client.get_pull(number=obj._id)
            comments = pull.get_comments()
        else:
            return []

        return [
            Comment(
                body=comment.body,
                created_at=comment.created_at,
                author=self.get_user_data(comment.user),
            )
            for comment in comments
        ]

    @log_exceptions(default_return=[], message="Failed to get invites from GitHub")
    def get_invites(self, repo: Repository) -> list[Invite]:
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

    def get_rate_limiting(self) -> tuple[int, int]:
        return self.client.rate_limiting

    @log_exceptions(default_return=[], message="Failed to get workflow runs from GitHub")
    def get_workflow_runs(self, repo) -> list[WorkflowRun]:
        runs = self.client.get_repo(repo._id).get_workflow_runs()
        return [
            WorkflowRun(
                display_title=r.display_title,
                event=r.event,
                head_branch=r.head_branch,
                head_sha=r.head_sha,
                name=r.name,
                path=r.path,
                created_at=r.created_at,
                run_started_at=r.run_started_at,
                updated_at=r.updated_at,
                conclusion=r.conclusion,
                status=r.status,
                url=r.url,
            )
            for r in runs
        ]

    def get_base_url(self) -> str:
        return 'https://api.github.com'


# Точка входа для тестирования
if __name__ == "__main__":
    # Создайте клиент GitHub (используйте ваш токен)
    # client = Github("")
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
