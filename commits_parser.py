from utils import logger
import pytz
from time import sleep
from github import Github, Repository
import GitHubRepoAPI  # Импортируем обёртку

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

def log_repository_commits(client: Github, repository, csv_name, start, finish, branch):
    branches = []
    match branch:
        case 'all':
            api = GitHubRepoAPI(client)
            branches = api.get_branches(repository)
            for branch in branches:
                branches.append(branch.name)
        case None:
            branches.append(repository.default_branch)
        case _:
            branches.append(branch)

    for branch in branches:
        print(f'Processing branch {branch}')
        # Используем обёртку для получения коммитов
        api = GitHubRepoAPI(repository._github)
        commits = api.get_commits(repository)
        for commit in commits:
            if (
                commit.date.astimezone(pytz.timezone(TIMEZONE)) < start
                or commit.date.astimezone(pytz.timezone(TIMEZONE)) > finish
            ):
                continue
            commit_data = [
                repository.full_name,
                commit.author.username,
                commit.author.email or EMPTY_FIELD,
                commit.date,
                '; '.join([file.filename for file in commit.files]),
                commit._id,
                branch,
            ]
            info = dict(zip(FIELDNAMES, commit_data))

            logger.log_to_csv(csv_name, FIELDNAMES, info)
            logger.log_to_stdout(info)

            sleep(TIMEDELTA)

def log_commits(
    client: Github, working_repos, csv_name, start, finish, branch, fork_flag
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    api = GitHubRepoAPI(client)  # Используем обёртку

    for repo_name in working_repos:
        try:
            # Получаем репозиторий через обёртку
            repo = api.get_repository(repo_name)
            if not repo:
                print(f"Repository {repo_name} not found or access denied.")
                continue

            logger.log_title(repo.name)
            log_repository_commits(repo, csv_name, start, finish, branch)
            if fork_flag:
                # Получаем форки через оригинальный метод, так как его нет в обёртке(Нужно добавить)
                forked_repos = client.get_repo(repo._id).get_forks()
                for forked_repo in forked_repos:
                    logger.log_title("FORKED:", forked_repo.full_name)
                    log_repository_commits(forked_repo, csv_name, start, finish, branch)
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)
