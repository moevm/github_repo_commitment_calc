from utils import logger
from time import sleep
from typing import Generator
from interface_wrapper import IRepositoryAPI, Repository

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'
FIELDNAMES = (
    'repository name',
    'login',
    'name',
    'email',
    'url',
    'permissions',
    'total_commits',
    'id',
    'node_id',
    'type',
    'bio',
    'site_admin',
)

def log_repository_contributors(client: IRepositoryAPI, repository: Repository, csv_name: str):
    contributors_stats = get_contributors_stats(client, repository)

    nvl = lambda val: val or EMPTY_FIELD

    for contributor_stat in contributors_stats.values():
        contributor = contributor_stat["contributor_object"]
        contributor_permissons = repository.get_collaborator_permission(contributor)

        info_tmp = {
            'repository name': repository.full_name,
            'login': contributor.login,
            'name': nvl(contributor.name),
            'email': nvl(contributor_stat['email']),
            'url': contributor.html_url,
            'permissions': nvl(contributor_permissons),
            'total_commits': contributor_stat['total_commits'],
            'id': contributor.id,
            'node_id': contributor.node_id,
            'type': contributor.type,
            'bio': nvl(contributor.bio),
            'site_admin': contributor.site_admin,
        }

        logger.log_to_csv(csv_name, FIELDNAMES, info_tmp)
        logger.log_to_stdout(info_tmp)

        sleep(TIMEDELTA)

def get_contributors_stats(client: IRepositoryAPI, repository: Repository) -> dict:
    contributors_stats = dict()

    # Используем обёртку для получения коммитов
    commits = client.get_commits(repository)

    for commit in commits:
        contributor = commit.author

        if not contributor.login in contributors_stats:
            contributors_stats[contributor.login] = {
                'total_commits': 0,
                'email': commit.commit.author.email,
                'contributor_object': contributor,
            }

        contributors_stats[contributor.login]['total_commits'] += 1

        sleep(TIMEDELTA)

    return contributors_stats

def log_contributors(
    client: IRepositoryAPI, working_repos: Generator, csv_name: str, fork_flag: bool
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for repo in working_repos:
        try:
            logger.log_title(repo.full_name)
            log_repository_contributors(repo, csv_name)

            if fork_flag:
                for forked_repo in client.get_forks():
                    logger.log_title("FORKED:", forked_repo.name)
                    log_repository_contributors(client, forked_repo, csv_name)
                    sleep(TIMEDELTA)

        except e:
            print(e)
            exit(1)
