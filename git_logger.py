from interface_wrapper import RepositoryFactory, IRepositoryAPI
from time import sleep

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
        # Возможно это можно переписать покрасивее
        if source == 'github':
            self.clients = self._init_clients(source, tokens, base_url)
        elif base_url == 'forgejo':
            self.client = RepositoryFactory.create_api(source, tokens[0], base_url)
            self.token = tokens[0]
        else:
            print(f"Unavailable source {source}, use [ 'github' | 'forgejo' ] instead")

        self.source = source

    def _init_clients(
        self, source: str, tokens: list[str], base_url: str | None
    ) -> list[dict]:
        clients = [
            {
                "client": RepositoryFactory.create_api(source, token, base_url),
                "token": token,
            }
            for token in tokens
        ]

        return clients

    def _get_next_git_client(self) -> tuple[IRepositoryAPI, str]:
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

        return client['client'], client['token']

    def _get_next_forgejo_client(self) -> tuple[IRepositoryAPI, str]:
        return self.client, self.token

    def get_next_client(self) -> tuple[IRepositoryAPI, str]:
        if self.source == 'github':
            return self._get_next_git_client()
        elif self.source == 'forgejo':
            return self._get_next_forgejo_client


def get_next_binded_repo(clients: Clients, repositories: list[str]):
    for repo_name in repositories:
        try:
            client, token = clients.get_next_client()
            repo = client.get_repository(repo_name)
        except Exception as err:
            print(f'get_next_repo(): error {err}')
            print(f'get_next_repo(): failed to load repository "{repo_name}"')
            exit(1)
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
