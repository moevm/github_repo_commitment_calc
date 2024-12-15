import csv
import pytz
from time import sleep
from github import Github, Repository, GithubException, PullRequest

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'
FIELDNAMES = ('repository name', 'author name', 'author login', 'author email', 'date and time', 'changed files', 'commit id', 'branch')
GOOGLE_MAX_CELL_LEN = 50000


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
        # TODO add support of since and until in https://pygithub.readthedocs.io/en/stable/github_objects/Repository.html#github.Repository.Repository.get_commits
        for commit in repository.get_commits(sha=branch):
            if commit.commit.author.date.astimezone(
                    pytz.timezone(TIMEZONE)) < start or commit.commit.author.date.astimezone(
                pytz.timezone(TIMEZONE)) > finish:
                continue
            if commit.commit is not None:
                nvl = lambda val: val or EMPTY_FIELD
                changed_files = '; '.join([file.filename for file in commit.files])
                if len(changed_files) > GOOGLE_MAX_CELL_LEN:
                    changed_files = changed_files[:GOOGLE_MAX_CELL_LEN]
                commit_data = [repository.full_name, commit.commit.author.name, nvl(commit.author.login), nvl(commit.commit.author.email),
                               commit.commit.author.date, changed_files, commit.commit.sha, branch]
                info = dict(zip(FIELDNAMES, commit_data))

                log_commit_to_csv(info, csv_name)
                log_commit_to_stdout(info)
                sleep(TIMEDELTA)


def log_commits(client: Github, working_repos, csv_name, start, finish, branch, fork_flag):
    with open(csv_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(FIELDNAMES)


    for repo in working_repos:
        try:
            print('=' * 20, repo.full_name, '=' * 20)
            log_repository_commits(repo, csv_name, start, finish, branch)
            if fork_flag:
                for forked_repo in repo.get_forks():
                    print('=' * 20, "FORKED:", forked_repo.full_name, '=' * 20)
                    log_repository_commits(forked_repo, csv_name, start, finish, branch)
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)
