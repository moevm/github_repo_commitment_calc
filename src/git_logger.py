from time import sleep
import logging
import traceback

import requests

from src.GitHubRepoAPI import GitHubRepoAPI
from src.interface_wrapper import (
    RepositoryFactory,
    IRepositoryAPI
)
from src.constants import (
    TIMEDELTA,
)


def login(token, base_url):
    try:
        client = RepositoryFactory.create_api(token, base_url)
        return client
    except Exception as e:
        logging.error(e)
        logging.error(traceback.format_exc())
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
            if base_url:
                raise Exception("No valid tokens for either GitHub or Forgejo")
            raise Exception("Make sure that base_url is provided")

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


def get_assignee_story(git_object, client, token, repository):
    assignee_result = ""

    repo_owner = repository.owner.login
    repo_name = repository.name
    issue_index = getattr(git_object, "number", None) or getattr(git_object, "index", None) or getattr(git_object, "_id", None)  # Для pull request и issue одинаково
    print(issue_index)

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

    results = [
        f"{event.get('created_at')}: {event.get('actor', {}).get('login', 'unknown')} -"
        + ("/" if event.get('event') == "unassigned" else "")
        + f"> {event.get('assignee', {}).get('login', 'unknown')}; "
        for event in events 
        if event.get('event') in ["assigned", "unassigned"]
    ]
    assignee_result = ''.join(results)

    return assignee_result
