from utils import logger
import pytz
from time import sleep

# from github import Github, Repository, GithubException, PullRequest
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


def log_commit_to_csv(info, csv_name):
    with open(csv_name, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writerow(info)


def log_commit_to_stdout(info):
    print(info)


def log_repository_commits(repository: Repository, csv_name, start, finish, branch):
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
            if commit.commit is not None:
                nvl = lambda val: val or EMPTY_FIELD
                commit_data = [repository.full_name, commit.commit.author.name, nvl(commit.author.login), nvl(commit.commit.author.email),
                               commit.commit.author.date, '; '.join([file.filename for file in commit.files]), commit.commit.sha, branch]
                info = dict(zip(FIELDNAMES, commit_data))

            logger.log_to_csv(csv_name, FIELDNAMES, info)
            logger.log_to_stdout(info)

            sleep(TIMEDELTA)


def log_commits(
    client: IRepositoryAPI, working_repos, csv_name, start, finish, branch, fork_flag
):
    logger.log_to_csv(csv_name, FIELDNAMES)

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
