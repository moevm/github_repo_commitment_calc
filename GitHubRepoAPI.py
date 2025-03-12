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