import base64
import sys
import logging

import isodate
from pyforgejo import PyforgejoApi

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
    WorkflowRun
)


class ForgejoRepoAPI(IRepositoryAPI):
    def __init__(self, client):
        self.client = client

    def get_user_data(self, user) -> User:
        return User(
            login=user.login,
            username=getattr(user, 'full_name', "No name"),
            email=getattr(user, 'email', ""),
            html_url=user.html_url,
            node_id=user.id,
            type=getattr(user, 'type', ""),
            bio=getattr(user, 'bio', ""),
            site_admin=user.site_admin if hasattr(user, 'site_admin') else False,
            _id=user.id,
        )

    @log_exceptions(default_return=None, message="Failed to get repository")
    def get_repository(self, id: str) -> Repository | None:
        repo = self.client.repository.repo_get(
            owner=id.split('/')[0], repo=id.split('/')[1]
        )
        if not repo:
            logging.error(f"Failed to get repository {id} from Forgejo.")
            return None

        return Repository(
            _id=repo.full_name,
            name=repo.name,
            url=repo.html_url,
            default_branch=Branch(name=repo.default_branch, last_commit=None),
            owner=self.get_user_data(repo.owner),
        )

    @log_exceptions(default_return="Error", message="Failed to get collaborator permission")
    def get_collaborator_permission(self, repo: Repository, user: User) -> str:
        permission = self.client.repository.repo_get_repo_permissions(
            owner=repo.owner.login, repo=repo.name, collaborator=user.login
        )
        return permission.permission

    @log_exceptions(default_return=[], message="Failed to get commits from Forgejo")
    def get_commits(self, repo: Repository, files: bool = True) -> list[Commit]:
        commits = self.client.repository.repo_get_all_commits(
            repo.owner.login, repo.name
        )
        return [
            Commit(
                _id=c.sha,
                message=c.commit.message,
                author=self.get_user_data(c.author) if c.author else None,
                date=isodate.parse_datetime(c.commit.author.date),
                files=(
                    [f.filename for f in getattr(c, "files", [])] if files else None
                ),
                additions=None,  # TODO
                deletions=None,  # TODO
            )
            for c in commits
        ]

    @log_exceptions(default_return=[], message="Failed to get contributors from Forgejo")
    def get_contributors(self, repo: Repository) -> list[Contributor]:
        commits = self.client.repository.repo_get_all_commits(
            repo.owner.login, repo.name
        )
        contributors = {
            c.author.login: c.author.email or "" for c in commits if c.author
        }
        return [Contributor(login, email) for login, email in contributors.items()]

    @log_exceptions(default_return=[], message="Failed to get issues from Forgejo")
    def get_issues(self, repo: Repository) -> list[Issue]:
        issues = self.client.issue.list_issues(repo.owner.login, repo.name)
        return [
            Issue(
                _id=i.id,
                title=i.title,
                state=i.state,
                created_at=i.created_at,
                closed_at=i.closed_at if i.state == 'closed' else None,
                closed_by=(
                    self.get_user_data(i.closed_by)
                    if hasattr(i, 'closed_by') and i.closed_by
                    else None
                ),
                body=i.body,
                user=self.get_user_data(i.user),
                labels=[label.name for label in i.labels],
                milestone=i.milestone.title if i.milestone else None,
            )
            for i in issues
        ]

    @log_exceptions(default_return=[], message="Failed to get pull requests from Forgejo")
    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
        pulls = self.client.repository.repo_list_pull_requests(
            repo.owner.login, repo.name
        )
        return [
            PullRequest(
                _id=p.number,
                title=p.title,
                author=self.get_user_data(p.user),
                state=p.state,
                created_at=p.created_at,
                head_label=p.head.ref,
                base_label=p.base.ref,
                head_ref=p.head.ref,
                base_ref=p.base.ref,
                merged_by=self.get_user_data(p.merged_by) if p.merged_by else None,
                files=[],  # TODO если возможно
                issue_url=None,  # TODO если возможно
                labels=[label.name for label in p.labels] if p.labels else [],
                milestone=p.milestone.title if p.milestone else None,
            )
            for p in pulls
        ]

    @log_exceptions(default_return=[], message="Failed to get branches from Forgejo")
    def get_branches(self, repo: Repository) -> list[Branch]:
        branches = self.client.repository.repo_list_branches(
            repo.owner.login, repo.name
        )
        result = []

        for branch in branches:
            commit = branch.commit

            author = commit.author
            contributor = Contributor(
                username=author.username if author else "unknown",
                email=author.email if author and author.email else "",
            )

            commit_details = self.client.repository.repo_get_single_commit(
                repo.owner.login, repo.name, commit.id
            )
            files = [file.filename for file in getattr(commit_details, "files", [])]

            commit_obj = Commit(
                _id=commit.id,
                message=commit.message,
                author=contributor,
                date=commit.timestamp,
                files=files,
            )

            result.append(Branch(name=branch.name, last_commit=commit_obj))

        return result

    @log_exceptions(default_return=[], message="Failed to get wiki pages from Forgejo")
    def get_wiki_pages(self, repo: Repository) -> list[WikiPage]:
        pages = self.client.repository.repo_get_wiki_pages(
            repo.owner.login, repo.name
        )
        result = []

        for page in pages:
            page_details = self.client.repository.repo_get_wiki_page(
                repo.owner.login, repo.name, page.title
            )

            wiki_page = WikiPage(
                title=page_details.title,
                content=base64.b64decode(page_details.content_base_64).decode('utf-8'),
            )
            result.append(wiki_page)

        return result

    @log_exceptions(default_return=[], message="Failed to get forks from Forgejo")
    def get_forks(self, repo: Repository) -> list[Repository]:
        forks = self.client.repository.list_forks(repo.owner.login, repo.name)
        result = []

        for fork in forks:
            default_branch = Branch(name=fork.default_branch, last_commit=None)
            owner = fork.owner

            result.append(
                Repository(
                    _id=fork.full_name,
                    name=fork.name,
                    url=fork.html_url,
                    default_branch=default_branch,
                    owner=owner,
                )
            )
        return result

    @log_exceptions(default_return=[], message="Failed to get comments for Forgejo")
    def get_comments(self, repo, obj) -> list[Comment]:
        result = []
        if isinstance(obj, Issue):
            comments = self.client.issue.get_repo_comments(
                repo.owner.login, repo.name
            )
            result = [
                Comment(
                    body=c.body,
                    created_at=c.created_at,
                    author=self.get_user_data(c.user),
                )
                for c in comments
            ]

        elif isinstance(obj, PullRequest):
            comments = self.client.repository.repo_get_pull_review_comments(
                repo.owner.login, repo.name, obj._id, 100000
            )  # нет id комментария
            result = [
                Comment(
                    body=c.body,
                    created_at=c.created_at,
                    author=self.get_user_data(c.user),
                )
                for c in comments
            ]
        return result

    @log_exceptions(default_return=[], message="Failed to simulate invites for Forgejo")
    def get_invites(self, repo: Repository, users: list[User] = None) -> list[Invite]:
        if users is None:
            return []
        collaborators = self.client.repository.repo_list_collaborators(
            owner=repo.owner.login, repo=repo.name
        )
        collab_logins = {c.login for c in collaborators}

        invites = []
        for user in users:
            if user.login not in collab_logins:
                invites.append(
                    Invite(
                        _id=0,
                        invitee=user,
                        created_at=None,
                        html_url=user.html_url,
                    )
                )
        return invites

    def get_rate_limiting(self) -> tuple[int, int]:
        return sys.maxsize, sys.maxsize

    def get_workflow_runs(self, repo) -> list[WorkflowRun]:
        return []

    def get_base_url(self) -> str:
        return self.client._client_wrapper.get_base_url()


# Точка входа для тестирования
if __name__ == "__main__":
    client = PyforgejoApi(api_key="token", base_url="https://codeberg.org/api/v1")
    api = ForgejoRepoAPI(client)

    repo = api.get_repository("harabat/pyforgejo")
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

    # Получение приглашений
    test_users = [
        User(login="user1", username="User One", email="", html_url="", node_id="",
             type="", bio="", site_admin=False, _id=""),
        User(login="user2", username="User Two", email="", html_url="", node_id="",
             type="", bio="", site_admin=False, _id=""),
    ]

    invites = api.get_invites(repo, users=test_users)
    print(f"Total Invites: {len(invites)}")

    for invite in invites:
        print(f"Invitee: {invite.invitee.username}, URL: {invite.html_url}")
