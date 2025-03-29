from dataclasses import dataclass, asdict
import pytz
from time import sleep

from utils import logger
from interface_wrapper import IRepositoryAPI, Repository

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'

GOOGLE_MAX_CELL_LEN = 50000


@dataclass(kw_only=True, frozen=True)
class CommitData:
    repository_name: str = ''
    author_name: str = ''
    author_email: str = ''
    datetime: str = ''
    changed_files: str = ''
    commit_id: str = ''
    branch: str = ''


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
                author_email=commit.author.email or EMPTY_FIELD,
                datetime=commit.date.astimezone(pytz.timezone(TIMEZONE)).isoformat(),
                changed_files=changed_files,
                commit_id=commit._id,
                branch=branch,
            )
            info = asdict(commit_data)

            logger.log_to_csv(csv_name, list(info.keys()), info)
            logger.log_to_stdout(info)

            sleep(TIMEDELTA)


def log_commits(
    client: IRepositoryAPI, working_repos, csv_name, start, finish, branch, fork_flag
):
    info = asdict(CommitData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for repo, token in working_repos:
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
