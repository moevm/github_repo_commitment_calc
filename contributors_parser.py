import csv
from time import sleep
from github import Github, Repository
import requests

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'
FIELDNAMES = ('repository name', 'login', 'name', 'email', 'url', 'permissions', 'total_commits', 'id', 'node_id', 'type', 'bio', 'site_admin')


def log_contributors_to_csv(info:dict, csv_name:str):
    with open(csv_name, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writerow(info)


def log_repository_contributors(repository: Repository, csv_name:str, token:str):

    contributors = repository.get_contributors()
    total_commits_dict = get_contributor_commits(repository.owner, repository.name, token)
    nvl = lambda val: val or EMPTY_FIELD
    for contributor in contributors:
        contributor_permissons = repository.get_collaborator_permission(contributor)
        contributor_total_commits = total_commits_dict.get(contributor.login, EMPTY_FIELD)

        info_tmp = {
            'repository name': repository.full_name,
            'login': contributor.login,
            'name': nvl(contributor.name),
            'email': nvl(contributor.email),
            'url': contributor.html_url,
            'permissions': nvl(contributor_permissons),
            'total_commits': contributor_total_commits,
            'id': contributor.id,
            'node_id': contributor.node_id,
            'type': contributor.type,
            'bio': nvl(contributor.bio),
            'site_admin': contributor.site_admin,
        }
        log_contributors_to_csv(info_tmp, csv_name)
        print(info_tmp)
        sleep(TIMEDELTA)


def log_contributors(client: Github, token:str, working_repos:list, csv_name:str, fork_flag:str):
    with open(csv_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(FIELDNAMES)

    for repo in working_repos:
        try:
            print('=' * 20, repo.full_name, '=' * 20)
            log_repository_contributors(repo, csv_name,token)
            if fork_flag:
                for forked_repo in repo.get_forks():
                    print('=' * 20, "FORKED:", forked_repo.full_name, '=' * 20)
                    log_repository_contributors(forked_repo, csv_name)
        except Exception as e:
            print(e)

def get_contributor_commits(repo_owner, repo_name, token):
    headers = {"Authorization": f"Bearer {token}"}
    request_name = f"https://api.github.com/repos/{repo_owner.login}/{repo_name}/stats/contributors"
    request = requests.get(request_name, headers=headers)

    while request.status_code == 202:
        print("Waiting for response...")
        sleep(10)
        request = requests.get(request_name, headers=headers)

    if request.status_code != 200:
        return {}
    
    response_data = request.json()
    total_commits_dict = {}
    for contributor in response_data:
        contributor_name = contributor["author"]["login"]
        total_commits = contributor["total"] 
        total_commits_dict[contributor_name] = total_commits
    return total_commits_dict