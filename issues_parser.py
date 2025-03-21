from utils import logger
import pytz
import requests
import json
from time import sleep
from git_logger import get_assignee_story
from github import Github, Repository, GithubException, PullRequest
import GitHubRepoAPI  # Импортируем обёртку

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'
FIELDNAMES = (
    'repository name',
    'number',
    'title',
    'state',
    'task',
    'created at',
    'creator name',
    'creator login',
    'creator email',
    'closer name',
    'closer login',
    'closer email',
    'closed at',
    'comment body',
    'comment created at',
    'comment author name',
    'comment author login',
    'comment author email',
    'assignee story',
    'connected pull requests',
    'labels',
    'milestone',
)

def get_connected_pulls(issue_number, repo_owner, repo_name, token):
    access_token = token
    repo_owner = repo_owner.login
    # Формирование запроса GraphQL
    query = """
    {
      repository(owner: "%s", name: "%s") {
        issue(number: %d) {
          timelineItems(first: 50, itemTypes:[CONNECTED_EVENT,CROSS_REFERENCED_EVENT]) {
            filteredCount
            nodes {
              ... on ConnectedEvent {
                ConnectedEvent: subject {
                  ... on PullRequest {
                    number
                    title
                    url
                  }
                }
              }
              ... on CrossReferencedEvent {
                CrossReferencedEvent: source {
                  ... on PullRequest {
                    number
                    title
                    url
                  }
                }
              }
            }
          }
        }
      }
    }""" % (
        repo_owner,
        repo_name,
        issue_number,
    )

    # Формирование заголовков запроса
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Отправка запроса GraphQL
    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        data=json.dumps({"query": query}),
    )
    response_data = response.json()
    # Обработка полученных данных
    pull_request_data = response_data["data"]["repository"]["issue"]
    list_url = []
    if pull_request_data is not None:
        issues_data = pull_request_data["timelineItems"]["nodes"]
        for pulls in issues_data:
            if (
                pulls.get("CrossReferencedEvent") != None
                and pulls.get("CrossReferencedEvent").get("url") not in list_url
            ):
                list_url.append(pulls.get("CrossReferencedEvent").get("url"))
            if (
                pulls.get("ConnectedEvent") != None
                and pulls.get("ConnectedEvent").get("url") not in list_url
            ):
                list_url.append(pulls.get("ConnectedEvent").get("url"))
        if list_url == []:
            return 'Empty field'
        else:
            return ';'.join(list_url)
    return 'Empty field'

def log_repository_issues(client: Github, repository: Repository, csv_name, token, start, finish):
    api = GitHubRepoAPI(client)
    issues = api.get_issues(repository)
    for issue in issues:
        if (
            issue.created_at.astimezone(pytz.timezone(TIMEZONE)) < start
            or issue.created_at.astimezone(pytz.timezone(TIMEZONE)) > finish
        ):
            continue
        nvl = lambda val: val or EMPTY_FIELD
        get_info = lambda obj, attr: EMPTY_FIELD if obj is None else getattr(obj, attr)
        info_tmp = {
            'repository name': repository.full_name,
            'number': issue.number,
            'title': issue.title,
            'state': issue.state,
            'task': issue.body,
            'created at': issue.created_at,
            'creator name': get_info(issue.user, 'name'),
            'creator login': get_info(issue.user, 'login'),
            'creator email': get_info(issue.user, 'email'),
            'closed at': nvl(issue.closed_at),
            'closer name': get_info(issue.closed_by, 'name'),
            'closer login': get_info(issue.closed_by, 'login'),
            'closer email': get_info(issue.closed_by, 'email'),
            'comment body': EMPTY_FIELD,
            'comment created at': EMPTY_FIELD,
            'comment author name': EMPTY_FIELD,
            'comment author login': EMPTY_FIELD,
            'comment author email': EMPTY_FIELD,
            'assignee story': get_assignee_story(issue),
            'connected pull requests': (
                EMPTY_FIELD
                if issue.number is None
                else get_connected_pulls(
                    issue.number, repository.owner, repository.name, token
                )
            ),
            'labels': (
                EMPTY_FIELD
                if issue.labels is None
                else ';'.join([label.name for label in issue.labels])
            ),
            'milestone': get_info(issue.milestone, 'title'),
        }
        #Нужно добавить
        if issue.get_comments().totalCount > 0:
            for comment in issue.get_comments():
                info = info_tmp
                info['comment body'] = comment.body
                info['comment created at'] = comment.created_at
                info['comment author name'] = comment.user.name
                info['comment author login'] = comment.user.login
                info['comment author email'] = comment.user.email

                logger.log_to_csv(csv_name, FIELDNAMES, info)
                logger.log_to_stdout(info)
        else:
            logger.log_to_csv(csv_name, FIELDNAMES, info_tmp)
            logger.log_to_stdout(info_tmp)

        sleep(TIMEDELTA)

def log_issues(client: Github, working_repo, csv_name, token, start, finish, fork_flag):
    logger.log_to_csv(csv_name, FIELDNAMES)

    api = GitHubRepoAPI(client)  # Используем обёртку

    for repo_name in working_repo:
        try:
            # Получаем репозиторий через обёртку
            repo = api.get_repository(repo_name)
            if not repo:
                print(f"Repository {repo_name} not found or access denied.")
                continue

            logger.log_title(repo.name)
            log_repository_issues(repo, csv_name, token, start, finish)
            if fork_flag:
                # Получаем форки через оригинальный метод, так как его нет в обёртке(Нужно добавить get_forks)
                forked_repos = client.get_repo(repo._id).get_forks()
                for forked_repo in forked_repos:
                    logger.log_title("FORKED:", forked_repo.full_name)
                    log_repository_issues(forked_repo, csv_name, token, start, finish)
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)