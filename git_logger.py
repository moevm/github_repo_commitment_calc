from time import sleep
from interface_wrapper import IRepositoryAPI, RepositoryFactory, IClients

TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'


def login(token):
    if 1:
        client = RepositoryFactory.create_api("github", token)
    # except Exception as err:
    #     print(f'Github: Connect: error {err}')
    #     print('Github: Connect: user could not be authenticated please try again.')
    #     exit(1)
    # else:
        return client


def get_tokens_from_file(tokens_path: str) -> list[str]:
    with open(tokens_path, 'r') as file:
        tokens = [token for token in file.read().split('\n') if token]

    return tokens


class GithubClients(IClients):
    def __init__(self, tokens: list[str]):
        self.clients = self._init_clients(tokens)
        self.cur_client = None
        self.last_client = -1

    def _init_clients(self, tokens: list[str]) -> list[dict]:
        clients = [{"client": login(token), "token": token} for token in tokens]
        # нужно ли нам рейзить ошибку в случае 403, или просто временно пропускать эти токены?

        return clients

    def get_next_client(self):
        if not self.clients:
            raise Exception("No github-clients available")

        self.last_client = (self.last_client + 1) % len(self.clients)
        self.cur_client = self.clients[self.last_client]
        return self.cur_client



def get_next_repo(clients: IClients, repositories):
    with open(repositories, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]
    print(list_repos)
    for repo_name in list_repos:
        if 1:
            cur_client = clients.get_next_client()
            repo = cur_client['client'].get_repository(repo_name)
            if not repo:
                raise Exception(f"Repository {repo_name} not found.")
        # except Exception as err:
        #     print(f'Github: Connect: error {err}')
        #     print(f'Github: Connect: failed to load repository "{repo_name}"')
        #     exit(1)
        # else:
            yield repo


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
