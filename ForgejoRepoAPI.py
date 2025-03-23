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
    def __init__ (self, client):
        self.client = client

    def get_user_data(self, user) -> User:
        return User(
            login=user.login,
            username=getattr(user, 'full_name',"No name"),
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
        return " "

    def get_commits(self, repo: Repository, files: bool = True) -> list[Commit]:
        return []

    def get_contributors(self, repo: Repository) -> list[Contributor]:
        return []

    def get_issues(self, repo: Repository) -> list[Issue]:
        return []

    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
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

