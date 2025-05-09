from interface_wrapper import (
    RepositoryFactory,
    IRepositoryAPI
)
from GitHubRepoAPI import GitHubRepoAPI
from time import sleep
import requests

TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'


def login(source, token, base_url):
    client = RepositoryFactory.create_api(source, token, base_url)
    return client


def get_tokens_from_file(tokens_path: str) -> list[str]:
    with open(tokens_path, 'r') as file:
        tokens = [token for token in file.read().split('\n') if token]

    return tokens


def get_repos_from_file(repos_path: str) -> list[str]:
    with open(repos_path, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]

    return list_repos


class Clients:
    def __init__(self, source: str, tokens: list[str], base_url: str | None = None):
        self.clients = self._init_clients(source, tokens, base_url)
        self.cur_client = None

    def _init_clients(self, source: str, tokens: list[str], base_url: str | None) -> list[dict]:
        clients = [{"client": login(source, token, base_url), "token": token} for token in tokens]
        return clients

    def get_next_client(self) -> IRepositoryAPI:
        client = None
        max_remaining_limit = -1

        for client_tmp in self.clients:
            remaining_limit, limit = client_tmp["client"].get_rate_limiting()

            # можно добавить вывод износа токена
            # можно дополнительно проверять на 403 и временно пропускать эти токены,
            # либо завести константу "минимальный коэффициент износа" и не трогать "изношенные" токены

            if remaining_limit > max_remaining_limit:
                client = client_tmp
                max_remaining_limit = remaining_limit

            sleep(TIMEDELTA)

        if client is None:
            raise Exception("No git clients available")

        self.cur_client = client
        return client


def get_next_repo(clients: Clients, repositories):
    with open(repositories, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]
    for repo_name in list_repos:
        try:
            cur_client = clients.get_next_client()
            repo = cur_client['client'].get_repository(repo_name)
        except Exception as err:
            print(f'get_next_repo(): error {err}')
            print(f'get_next_repo(): failed to load repository "{repo_name}"')
        else:
            yield cur_client['client'], repo, cur_client['token']


def get_next_binded_repo(clients: Clients, repositories: list[str]):
    for repo_name in repositories:
        try:
            cur_client = clients.get_next_client()
            repo = cur_client['client'].get_repository(repo_name)
        except Exception as err:
            print(f'get_next_binded_repo(): error {err}')
            print(f'get_next_binded_repo(): failed to load repository "{repo_name}"')
        else:
            yield cur_client['client'], repo, cur_client['token']


def get_assignee_story(git_object, client, token, repository):
    assignee_result = ""

    try:
        repo_owner = repository.owner.login
        repo_name = repository.name
        issue_index = git_object._id  # Для pull request и issue одинаково

        base_url = client.get_base_url().rstrip('/')

        url = f"{base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_index}/timeline"
        headers = {
            "Authorization": f"Bearer {token}" if client is GitHubRepoAPI else f"token {token}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch issue timeline: {response.status_code}, {response.text}")

        events = response.json()

        for event in events:
            if event.get('event') in ["assigned", "unassigned"]:
                date = event.get('created_at')
                assigner = event.get('actor', {}).get('login', 'unknown')
                assignee = event.get('assignee', {}).get('login', 'unknown')

                assignee_result += f"{date}: {assigner} -"
                if event['event'] == "unassigned":
                    assignee_result += "/"
                assignee_result += f"> {assignee}; "

                sleep(TIMEDELTA)

    except Exception as e:
        print(f"get_assignee_story(): error {e}")

    return assignee_result
