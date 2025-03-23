from pyforgejo import PyforgejoApi
from interface_wrapper import (
    logging,
    datetime,
    IRepositoryAPI,
    Repository,
    Commit,
    Branch,
    User,
    Contributor,
    Issue,
    PullRequest,
    WikiPage,
    Comment,
    Invite
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
            _id=user.id
        )

    def get_repository(self, id: str) -> Repository | None:
        try:
            repo = self.client.repository.repo_get(owner=id.split('/')[0], repo=id.split('/')[1])

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
        except Exception as e:
            logging.error(f"Failed to get repository {id} from Forgejo: {e}")
            return None

    def get_collaborator_permission(self, repo: Repository, user: User) -> str:
        return "|||"

    def get_commits(self, repo: Repository, files: bool = True) -> list[Commit]:
        try:
            commits = self.client.repository.repo_get_all_commits(repo.owner.login, repo.name)
            return [
                Commit(
                    _id=c.sha,
                    message=c.commit.message,
                    author=self.get_user_data(c.author),
                    date=c.commit.author.date,
                    files=[f.filename for f in getattr(c, "files", [])] if files else None
                )
                for c in commits
            ]
        except Exception as e:
            logging.error(
                f"Failed to get commits from Forgejo for repo {repo.name}: {e}"
            )
        return []

    def get_contributors(self, repo: Repository) -> list[Contributor]:
        try:
            commits = self.client.repository.repo_get_all_commits(repo.owner.login, repo.name)
            contributors = {c.author.login: c.author.email or "" for c in commits if c.author}
            return [Contributor(login, email) for login, email in contributors.items()]
        except Exception as e:
            logging.error(f"Failed to get contributors from Forgejo for repo {repo.name}: {e}")
            return []

    def get_issues(self, repo: Repository) -> list[Issue]:
        try:
            issues = self.client.issue.list_issues(repo.owner.login, repo.name)
            return [
                Issue(
                    _id=i.id,
                    title=i.title,
                    state=i.state,
                    created_at=i.created_at,
                    closed_at=i.closed_at if i.state == 'closed' else None,
                    closed_by=self.get_user_data(i.closed_by) if hasattr(i, 'closed_by') and i.closed_by else None,
                    body=i.body,
                    user=self.get_user_data(i.user),
                    labels=[label.name for label in i.labels],
                    milestone=i.milestone.title if i.milestone else None,
                )
                for i in issues
            ]
        except Exception as e:
            logging.error(f"Failed to get issues from Forgejo for repo {repo.name}: {e}")
            return []

    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
        try:
            pulls = self.client.repository.repo_list_pull_requests(repo.owner.login, repo.name)

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
                    files=[file.filename for file in p.files],
                    issue_url=p.issue_url,
                    labels=[label.name for label in p.labels] if p.labels else [],
                    milestone=p.milestone.title if p.milestone else None,
                )
                for p in pulls
            ]
        except Exception as e:
            logging.error(f"Failed to get pull requests from Forgejo for repo {repo.name}: {e}")
            return []

    def get_branches(self, repo: Repository) -> list[Branch]:
        return []

    def get_wiki_pages(self, repo: Repository) -> list[WikiPage]:
        return []

    def get_forks(self, repo: Repository) -> list[Repository]:
        return []

    def get_comments(self, obj) -> list[Comment]:
        return []

    def get_invites(self, repo: Repository) -> list[Invite]:
        return []

