from utils import logger
import pytz
import requests
import json
from time import sleep
from git_logger import get_assignee_story, GithubClients
from github import Github, Repository, GithubException, PullRequest
from git_logger import get_assignee_story
from interface_wrapper import IRepositoryAPI, PullRequest, Repository

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
    # TODO как-то заменить
    return
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
    client: IRepositoryAPI,
    repository: Repository,
    csv_name,
    token,
    start,
    finish,
    log_comments=False,
):
    pulls = client.get_pull_requests(repository)
    for pull in pulls:
        if (
            pull.created_at.astimezone(pytz.timezone(TIMEZONE)) < start
            or pull.created_at.astimezone(pytz.timezone(TIMEZONE)) > finish
        ):
            continue
        nvl = lambda val: val or EMPTY_FIELD
        get_info = lambda obj, attr: EMPTY_FIELD if obj is None else getattr(obj, attr)
        info_tmp = {
            'repository name': repository.name,
            'title': pull.title,
            'id': pull._id,
            'state': pull.state,
            'commit into': pull.base_label,
            'commit from': pull.head_label,
            'created at': pull.created_at,
            'creator name': nvl(pull.author.username),
            'creator login': pull.author.login,
            'creator email': pull.author.email,
            'changed files': '; '.join([file for file in pull.files]),
            'comment body': EMPTY_FIELD,
            'comment created at': EMPTY_FIELD,
            'comment author name': EMPTY_FIELD,
            'comment author login': EMPTY_FIELD,
            'comment author email': EMPTY_FIELD,
            'merger name': pull.merged_by.username if pull.merged_by else None,
            'merger login': pull.merged_by.login if pull.merged_by else None,
            'merger email': pull.merged_by.email if pull.merged_by else None,
            'source branch': pull.head_ref,
            'target branch': pull.base_ref,
            'assignee story': get_assignee_story(pull),
            'related issues': (
                EMPTY_FIELD
                if pull.issue_url is None
                else get_related_issues(
                    pull._id, repository.owner, repository.name, token
                )
            ),
            'labels': (
                EMPTY_FIELD
                if pull.labels is None
                else ';'.join([label for label in pull.labels])
            ),
            'milestone': get_info(pull.milestone, 'title'),
        }

        if log_comments:
            comments = client.get_comments(repo, pull)
            if len(comments) > 0:
                for comment in comments:
                    info = info_tmp
                    info['comment body'] = comment.body
                    info['comment created at'] = comment.created_at
                    info['comment author name'] = comment.author.name
                    info['comment author login'] = comment.author.login
                    info['comment author email'] = nvl(comment.author.email)

                    logger.log_to_csv(csv_name, FIELDNAMES, info)
                    logger.log_to_stdout(info)
        else:
            logger.log_to_csv(csv_name, FIELDNAMES, info_tmp)
            logger.log_to_stdout(info_tmp)
        sleep(TIMEDELTA)


def log_pull_requests(
    client: IRepositoryAPI,
    working_repos,
    csv_name,
    start,
    finish,
    fork_flag,
    log_comments=False,
):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for repo, token in working_repos:
        try:
            logger.log_title(repo.name)
            log_repositories_pr(
                client, repo, csv_name, token, start, finish, log_comments
            )
            if fork_flag:
                # Получаем форки через оригинальный метод, так как его нет в обёртке(Добавить)
                forked_repos = client.get_repo(repo._id).get_forks()
                for forked_repo in forked_repos:
                    logger.log_title("FORKED:", forked_repo.full_name)
                    log_repositories_pr(
                        client,
                        forked_repo,
                        csv_name,
                        token,
                        start,
                        finish,
                        log_comments,
                    )
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print(e)
