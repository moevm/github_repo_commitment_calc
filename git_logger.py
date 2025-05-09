from time import sleep

from constants import TIMEDELTA
from interface_wrapper import IRepositoryAPI, RepositoryFactory


def login(token, base_url):
    try:
        client = RepositoryFactory.create_api(token, base_url)
        return client
    except Exception:
        return None


def get_tokens_from_file(tokens_path: str) -> list[str]:
    with open(tokens_path, 'r') as file:
        tokens = [token for token in file.read().split('\n') if token]

    return tokens


def get_repos_from_file(repos_path: str) -> list[str]:
    with open(repos_path, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]

    return list_repos


class Clients:
    def __init__(self, tokens: list[str], base_url: str | None = None):
        self.clients = []
        self.token_map = {}

        for token in tokens:
            client = login(token, base_url)
            if client:
                self.clients.append(client)
                self.token_map[client] = token

        if not self.clients:
            raise Exception("No valid tokens for either GitHub or Forgejo")

    def _get_next_client(self) -> tuple[IRepositoryAPI, str]:
        client = None
        max_remaining_limit = -1

        for c in self.clients:
            remaining, _ = c.get_rate_limiting()
            if remaining > max_remaining_limit:
                client = c
                max_remaining_limit = remaining
            sleep(TIMEDELTA)

        if client is None:
            raise Exception("No git clients available")

        return client, self.token_map[client]

    def get_next_client(self) -> tuple[IRepositoryAPI, str]:
        return self._get_next_client()


def get_next_binded_repo(clients: Clients, repositories: list[str]):
    for repo_name in repositories:
        try:
            client, token = clients.get_next_client()
            repo = client.get_repository(repo_name)
        except Exception as err:
            print(f'git_logger.get_next_binded_repo(): error {err}')
            print(f'git_logger.get_next_binded_repo(): failed to load repository "{repo_name}"')
        else:
            yield client, repo, token


def get_assignee_story(git_object):
    # TODO
    return ""

    '''assignee_result = ""
    events = (
        git_object.get_issue_events()
        if type(github_object) is PullRequest.PullRequest
        else github_object.get_events()
    )
    for event in events:
        if event.event in ["assigned", "unassigned"]:
            date = event.created_at
            assigner = github_object.user.login
            assignee = event.assignee.login
            assignee_result += f"{date}: {assigner} -"
            if event.event == "unassigned":
                assignee_result += "/"
            assignee_result += f"> {assignee}; "
        sleep(TIMEDELTA)
    return assignee_result'''
