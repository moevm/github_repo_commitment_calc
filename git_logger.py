from time import sleep
from interface_wrapper import IRepositoryAPI, RepositoryFactory

TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'

def login(token):
    try:
        client = RepositoryFactory.create_api("github", token)
    except Exception as err:
        print(f'Github: Connect: error {err}')
        print('Github: Connect: user could not be authenticated please try again.')
        exit(1)
    else:
        return client

def get_next_repo(client: IRepositoryAPI, repositories):
    with open(repositories, 'r') as file:
        list_repos = [x for x in file.read().split('\n') if x]
    print(list_repos)
    for repo_name in list_repos:
        try:
            repo = client.get_repository(repo_name)
            if not repo:
                raise Exception(f"Repository {repo_name} not found.")
        except Exception as err:
            print(f'Github: Connect: error {err}')
            print(f'Github: Connect: failed to load repository "{repo_name}"')
            exit(1)
        else:
            yield repo

def get_assignee_story(github_object):
    #TODO
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
