from dataclasses import asdict, dataclass
from time import sleep
from typing import Generator

from src.constants import EMPTY_FIELD, TIMEDELTA
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger


@dataclass(kw_only=True, frozen=True)
class ContributorData:
    repository_name: str = ''
    login: str = ''
    name: str = ''
    email: str = ''
    url: str = ''
    permissions: str = ''
    total_commits: int = 0
    node_id: str = ''
    type: str = ''
    bio: str = ''
    site_admin: bool = False


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

        contributor_data = ContributorData(
            repository_name=repository.name,
            login=contributor.login,
            name=nvl(contributor.username),
            email=nvl(contributor_stat['email']),
            url=contributor.html_url,
            permissions=nvl(contributor_permissions),
            total_commits=contributor_stat['total_commits'],
            node_id=contributor.node_id,
            type=contributor.type,
            bio=nvl(contributor.bio),
            site_admin=contributor.site_admin,
        )

        info_dict = asdict(contributor_data)

        logger.log_to_csv(csv_name, list(info_dict.keys()), info_dict)
        logger.log_to_stdout(info_dict)

        sleep(TIMEDELTA)


def get_contributors_stats(client: IRepositoryAPI, repository: Repository) -> dict:
    contributors_stats = dict()
    commits = client.get_commits(repository, False)

    for commit in commits:
        contributor = commit.author

        if not contributor:
            continue

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
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    fork_flag: bool,
):
    info = asdict(ContributorData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        logger.log_title(repo.name)
        log_repository_contributors(client, repo, csv_name)

        if fork_flag:
            for forked_repo in client.get_forks(repo):
                logger.log_title(f"FORKED: {forked_repo.name}")
                log_repository_contributors(client, forked_repo, csv_name)
                sleep(TIMEDELTA)
