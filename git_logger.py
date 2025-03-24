from interface_wrapper import (
    RepositoryFactory,
    Repository,
    Branch,
    IRepositoryAPI
)
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
    # TODO
    return ""

    assignee_result = ""
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
    return assignee_result
