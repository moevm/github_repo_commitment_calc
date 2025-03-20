from utils import logger
import pytz
import requests
import json
from time import sleep
from git_logger import get_assignee_story
from github import Github, Repository, GithubException, PullRequest

EMPTY_FIELD = 'Empty field'
TIMEDELTA = 0.05
TIMEZONE = 'Europe/Moscow'
FIELDNAMES = (
    'repository name',
    'title',
    'id',
    'state',
    'commit into',
    'commit from',
    'created at',
    'creator name',
    'creator login',
    'creator email',
    'changed files',
    'comment body',
    'comment created at',
    'comment author name',
    'comment author login',
    'comment author email',
    'merger name',
    'merger login',
    'merger email',
    'source branch',
    'target branch',
    'assignee story',
    'related issues',
    'labels',
    'milestone',
)


def get_related_issues(pull_request_number, repo_owner, repo_name, token):
    access_token = token
    repo_owner = repo_owner.login

    # Формирование запроса GraphQL
    query = """
        {
          repository(owner: "%s", name: "%s") {
            pullRequest(number: %d) {
              id
              closingIssuesReferences(first: 50) {
                edges {
                  node {
                    id
                    body
                    number
                    title
                    url
                  }
                }
              }
            }
          }
        }
        """ % (
        repo_owner,
        repo_name,
        pull_request_number,
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
    pull_request_data = response_data["data"]["repository"]["pullRequest"]
    issues_data = pull_request_data["closingIssuesReferences"]["edges"]
    list_issues_url = []
    # сохранение информации об issues
    for issue in issues_data:
        issue_node = issue["node"]
        list_issues_url.append(issue_node["url"])
    return ';'.join(list_issues_url)


def log_repositories_pr(
    repository: Repository, csv_name, token, start, finish, log_comments=False
):
    for pull in repository.get_pulls(state='all'):
        if (
            pull.created_at.astimezone(pytz.timezone(TIMEZONE)) < start
            or pull.created_at.astimezone(pytz.timezone(TIMEZONE)) > finish
        ):
            continue
        nvl = lambda val: val or EMPTY_FIELD
        get_info = lambda obj, attr: EMPTY_FIELD if obj is None else getattr(obj, attr)
        info_tmp = {
            'repository name': repository.full_name,
            'title': pull.title,
            'id': pull.number,
            'state': pull.state,
            'commit into': pull.base.label,
            'commit from': pull.head.label,
            'created at': pull.created_at,
            'creator name': nvl(pull.user.name),
            'creator login': pull.user.login,
            'creator email': pull.user.email,
            'changed files': '; '.join([file.filename for file in pull.get_files()]),
            'comment body': EMPTY_FIELD,
            'comment created at': EMPTY_FIELD,
            'comment author name': EMPTY_FIELD,
            'comment author login': EMPTY_FIELD,
            'comment author email': EMPTY_FIELD,
            'merger name': get_info(pull.merged_by, 'name'),
            'merger login': get_info(pull.merged_by, 'login'),
            'merger email': get_info(pull.merged_by, 'email'),
            'source branch': pull.head.ref,
            'target branch': pull.base.ref,
            'assignee story': get_assignee_story(pull),
            'related issues': (
                EMPTY_FIELD
                if pull.issue_url is None
                else get_related_issues(
                    pull.number, repository.owner, repository.name, token
                )
            ),
            'labels': (
                EMPTY_FIELD
                if pull.labels is None
                else ';'.join([label.name for label in pull.labels])
            ),
            'milestone': get_info(pull.milestone, 'title'),
        }

        if log_comments:
            comments = pull.get_comments()
            if comments.totalCount > 0:
                for comment in comments:
                    info = info_tmp
                    info['comment body'] = comment.body
                    info['comment created at'] = comment.created_at
                    info['comment author name'] = comment.user.name
                    info['comment author login'] = comment.user.login
                    info['comment author email'] = nvl(comment.user.email)

                    logger.log_to_csv(csv_name, FIELDNAMES, info)
                    logger.log_to_stdout(info)
        else:
            logger.log_to_csv(csv_name, FIELDNAMES, info_tmp)
            logger.log_to_stdout(info_tmp)
        sleep(TIMEDELTA)


def log_pull_requests(
    client: Github,
    working_repos,
    csv_name,
    token,
    start,
    finish,
    fork_flag,
    log_comments=False,
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for repo in working_repos:
        try:
            logger.log_title(repo.full_name)
            log_repositories_pr(repo, csv_name, token, start, finish)
            if fork_flag:
                for forked_repo in repo.get_forks():
                    logger.log_title("FORKED:", forked_repo.full_name)
                    log_repositories_pr(
                        forked_repo, csv_name, token, start, finish, log_comments
                    )
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)
