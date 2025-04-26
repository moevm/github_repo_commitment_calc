from interface_wrapper import (
    RepositoryFactory,
    IRepositoryAPI
)
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


class GitClients:
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


def get_next_repo(clients: GitClients, repositories):
    with open(repositories, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]
    print(list_repos)
    for repo_name in list_repos:
        try:
            cur_client = clients.get_next_client()
            repo = cur_client['client'].get_repository(repo_name)
        except Exception as err:
            print(f'get_next_repo(): error {err}')
            print(f'get_next_repo(): failed to load repository "{repo_name}"')
            exit(1)
        else:
            print(cur_client['token'])
            yield repo, cur_client['token']


def get_assignee_story(git_object):
    assignee_result = ""

    try:
        repo_owner = git_object.repository.owner.username
        repo_name = git_object.repository.name
        issue_index = git_object.number  # Для pull request и issue одинаково

        client = git_object._client  # доступ к api-клиенту
        token = client.token
        base_url = client.base_url.rstrip('/')

        url = f"{base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_index}/timeline"
        headers = {
            "Authorization": f"token {token}",
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
