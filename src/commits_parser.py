from dataclasses import asdict, dataclass
from datetime import datetime
from time import sleep
from typing import Generator

import pytz

from src.constants import EMPTY_FIELD, GOOGLE_MAX_CELL_LEN, TIMEDELTA, TIMEZONE
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger


@dataclass(kw_only=True, frozen=True)
class CommitData:
    repository_name: str = ''
    author_name: str = ''
    author_login: str = ''
    author_email: str = ''
    date_and_time: str = ''
    changed_files: str = ''
    commit_id: str = ''
    branch: str = ''
    additions: str = ''
    deletions: str = ''


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
        print(f'Processing branch {branch}')
        commits = client.get_commits(repository)
        for commit in commits:
            if (
                commit.date.astimezone(pytz.timezone(TIMEZONE)) < start
                or commit.date.astimezone(pytz.timezone(TIMEZONE)) > finish
            ):
                continue

            changed_files = '; '.join([file for file in commit.files])
            changed_files = changed_files[:GOOGLE_MAX_CELL_LEN]
            commit_data = CommitData(
                repository_name=repository.name,
                author_name=commit.author.username,
                author_login=commit.author.login or EMPTY_FIELD,
                author_email=commit.author.email or EMPTY_FIELD,
                date_and_time=commit.date.astimezone(pytz.timezone(TIMEZONE)).isoformat(),
                changed_files=changed_files,
                commit_id=commit._id,
                branch=branch,
                additions=commit.additions,
                deletions=commit.deletions,
            )
            info = asdict(commit_data)

            logger.log_to_csv(csv_name, list(info.keys()), info)
            logger.log_to_stdout(info)

            sleep(TIMEDELTA)


def log_commits(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    branch: str,
    fork_flag: bool,
):
    info = asdict(CommitData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        logger.log_title(repo.name)
        log_repository_commits(client, repo, csv_name, start, finish, branch)
        if fork_flag:
            for forked_repo in client.get_forks(repo):
                logger.log_title(f"FORKED: {forked_repo.name}")
                log_repository_commits(
                    client, forked_repo, csv_name, start, finish, branch
                )
                sleep(TIMEDELTA)
        sleep(TIMEDELTA)
