from github import Github, GithubException, PullRequest
from interface_wrapper import (
    RepositoryFactory,
    Repository,
    Branch,
)
from time import sleep

TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'


def login(token):
    client = Github(login_or_token=token)

    try:
        client.get_user().login
    except GithubException as err:
        print(f'Github: Connect: error {err.data}')
        print('Github: Connect: user could not be authenticated please try again.')
        exit(1)
    else:
        return client


def get_tokens_from_file(tokens_path: str) -> list[str]:
    with open(tokens_path, 'r') as file:
        tokens = [token for token in file.read().split('\n') if token]

    return tokens


class GithubClients:
    def __init__(self, tokens: list[str]):
        self.clients = self._init_clients(tokens)
        self.cur_client = None

    def _init_clients(self, tokens: list[str]) -> list[dict]:
        clients = [{"client": login(token), "token": token} for token in tokens]
        for c in clients:
            c["api"] = RepositoryFactory.create_api("github", c["client"])

        return clients

    def get_next_client(self) -> Github:
        client = None
        max_remaining_limit = -1

        for client_tmp in self.clients:
            remaining_limit, limit = client_tmp["client"].rate_limiting

            # можно добавить вывод износа токена
            # можно дополнительно проверять на 403 и временно пропускать эти токены,
            # либо завести константу "минимальный коэффициент износа" и не трогать "изношенные" токены

            if remaining_limit > max_remaining_limit:
                client = client_tmp
                max_remaining_limit = remaining_limit

            sleep(TIMEDELTA)

        if client is None:
            raise Exception("No github-clients available")

        self.cur_client = client
        return client


def get_next_repo(clients: GithubClients, repositories):
    with open(repositories, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]
    print(list_repos)
    for repo_name in list_repos:
        try:
            cur_client = clients.get_next_client()
            repo = cur_client['client'].get_repo(repo_name)
        except GithubException as err:
            print(f'Github: Connect: error {err.data}')
            print(f'Github: Connect: failed to load repository "{repo_name}"')
            exit(1)
        else:
            print(cur_client['token'])
            yield Repository(
                _id=repo.full_name,
                name=repo.name,
                url=repo.html_url,
                default_branch=Branch(name=repo.default_branch, last_commit=None),
                owner=cur_client['api'].get_user_data(repo.owner),
            ), cur_client['token']


def get_assignee_story(github_object):
    # TODO
    return ""
    assignee_result = ""
    events = (
        github_object.get_issue_events()
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
