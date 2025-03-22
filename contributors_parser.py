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


def log_repository_contributors(
    client: IRepositoryAPI, repository: Repository, csv_name: str
):
    contributors_stats = get_contributors_stats(client, repository)

    def nvl(val):
        return val or EMPTY_FIELD

    for contributor_stat in contributors_stats.values():
        contributor = contributor_stat["contributor_object"]
        contributor_permissions = client.get_collaborator_permission(
            repository, contributor
        )

        info_tmp = {
            'repository name': repository.name,
            'login': contributor.login,
            'name': nvl(contributor.username),
            'email': nvl(contributor_stat['email']),
            'url': contributor.html_url,
            'permissions': nvl(contributor_permissions),
            'total_commits': contributor_stat['total_commits'],
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
    commits = client.get_commits(repository, False)

    for commit in commits:
        contributor = commit.author

        if contributor.login not in contributors_stats:
            contributors_stats[contributor.login] = {
                'total_commits': 0,
                'email': contributor.email,
                'contributor_object': contributor,
            }

        contributors_stats[contributor.login]['total_commits'] += 1

        sleep(TIMEDELTA)

    return contributors_stats


def log_contributors(
    client: IRepositoryAPI, working_repos: Generator, csv_name: str, fork_flag: bool
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for repo, token in working_repos:
        try:
            logger.log_title(repo.name)
            log_repository_contributors(client, repo, csv_name)

            if fork_flag:
                for forked_repo in client.get_forks(repo):
                    logger.log_title("FORKED:", forked_repo.name)
                    log_repository_contributors(client, forked_repo, csv_name)
                    sleep(TIMEDELTA)

        except Exception as e:
            print(e)
            exit(1)
