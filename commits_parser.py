from utils import logger
import pytz
from time import sleep
from interface_wrapper import IRepositoryAPI, IClients

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


def log_repository_commits(
    client: IRepositoryAPI, repository, csv_name, start, finish, branch
):
    branches = []
    match branch:
        case 'all':
            branches = client.get_branches(repository)
            for branch in branches:
                branches.append(branch.name)
        case None:
            branches.append(repository.default_branch)
        case _:
            branches.append(branch)

    for branch in branches:
        print(f'Processing branch {branch}')
        # Используем обёртку для получения коммитов
        commits = client.get_commits(repository)
        for commit in commits:
            if (
                commit.date.astimezone(pytz.timezone(TIMEZONE)) < start
                or commit.date.astimezone(pytz.timezone(TIMEZONE)) > finish
            ):
                continue
            commit_data = [
                repository.name,
                commit.author.username,
                commit.author.email or EMPTY_FIELD,
                commit.date,
                '; '.join([file for file in commit.files]),
                commit._id,
                branch,
            ]
            info = dict(zip(FIELDNAMES, commit_data))

            logger.log_to_csv(csv_name, FIELDNAMES, info)
            logger.log_to_stdout(info)

            sleep(TIMEDELTA)


def log_commits(
    clients: IClients, working_repos, csv_name, start, finish, branch, fork_flag
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for repo in working_repos:
        try:
            client = clients.get_next_client()
            logger.log_title(repo.name)
            log_repository_commits(client, repo, csv_name, start, finish, branch)
            if fork_flag:
                # TODO
                forked_repos = client.get_forks(repo)
                for forked_repo in forked_repos:
                    logger.log_title("FORKED:", forked_repo.name)
                    log_repository_commits(forked_repo, csv_name, start, finish, branch)
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)
