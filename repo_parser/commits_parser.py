from datetime import datetime
from typing import Generator
from utils import logger
import pytz
from time import sleep

from interface_wrapper import IRepositoryAPI, Repository

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'
FIELDNAMES = (
    'repository name',
    'author name',
    'author login',
    'author email',
    'date and time',
    'changed files',
    'commit id',
    'branch',
)
GOOGLE_MAX_CELL_LEN = 50000


def log_repository_commits(
    client: IRepositoryAPI, repository: Repository, csv_name, start, finish, branch
):
    branches = []
    match branch:
        case 'all':
            for branch in repository.get_branches():
                branches.append(branch.name)
        case None:
            branches.append(repository.default_branch)
        case _:
            branches.append(branch)

    for branch in branches:
        logger.log_to_stdout(f'Processing branch {branch}')

        commits = client.get_commits(repository)

        for commit in commits:
            if (
                commit.date.astimezone(pytz.timezone(TIMEZONE)) < start
                or commit.date.astimezone(pytz.timezone(TIMEZONE)) > finish
            ):
                continue

            changed_files = '; '.join([file for file in commit.files])
            info = {
                'repository name': repository.name,
                'author name': commit.author.username,
                'author login': commit.author.login,
                'author email': commit.author.email or EMPTY_FIELD,
                'date and time': commit.date,
                'changed files': changed_files[:GOOGLE_MAX_CELL_LEN],
                'commit id': commit._id,
                'branch': branch,
            }

            logger.log_to_csv(csv_name, FIELDNAMES, info)
            logger.log_to_stdout(info)

            sleep(TIMEDELTA)


def log_commits(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    branch: str,
    fork_flag: bool,
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for client, repo, token in binded_repos:
        try:
            logger.log_title(repo.name)
            log_repository_commits(client, repo, csv_name, start, finish, branch)
            if fork_flag:
                for forked_repo in client.get_forks(repo):
                    logger.log_title("FORKED:", forked_repo.full_name)
                    log_repository_commits(
                        client, forked_repo, csv_name, start, finish, branch
                    )
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)
