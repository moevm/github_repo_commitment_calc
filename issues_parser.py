import json
from dataclasses import asdict, dataclass
from time import sleep
from typing import Generator
from datetime import datetime

import pytz
import requests

from constants import EMPTY_FIELD, TIMEDELTA, TIMEZONE
from git_logger import get_assignee_story
from interface_wrapper import IRepositoryAPI, Repository
from utils import logger


@dataclass(kw_only=True, frozen=True)
class IssueData:
    repository_name: str = ''
    number: int = 0
    title: str = ''
    state: str = ''
    task: str = ''
    created_at: str = ''
    creator_name: str = ''
    creator_login: str = ''
    creator_email: str = ''
    closed_at: str | None = None
    closer_name: str | None = None
    closer_login: str | None = None
    closer_email: str | None = None
    assignee_story: str = ''
    connected_pull_requests: str = ''
    labels: str = ''
    milestone: str = ''


@dataclass(kw_only=True, frozen=True)
class IssueDataWithComment(IssueData):
    body: str = ''
    created_at: str = ''
    author_name: str = ''
    author_login: str = ''
    author_email: str = ''


def get_connected_pulls(issue_number, repo_owner, repo_name, token):
    # TODO как-то заменить
    return
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
                pulls.get("CrossReferencedEvent") is not None
                and pulls.get("CrossReferencedEvent").get("url") not in list_url
            ):
                list_url.append(pulls.get("CrossReferencedEvent").get("url"))
            if (
                pulls.get("ConnectedEvent") is not None
                and pulls.get("ConnectedEvent").get("url") not in list_url
            ):
                list_url.append(pulls.get("ConnectedEvent").get("url"))
        if list_url == []:
            return 'Empty field'
        else:
            return ';'.join(list_url)
    return 'Empty field'


def log_repository_issues(
    client: IRepositoryAPI, repository: Repository, csv_name, token, start, finish
):
    def nvl(val):
        return val or EMPTY_FIELD

    def get_info(obj, attr):
        return EMPTY_FIELD if obj is None else getattr(obj, attr)

    issues = client.get_issues(repository)

    for issue in issues:
        if (
            issue.created_at.astimezone(pytz.timezone(TIMEZONE)) < start
            or issue.created_at.astimezone(pytz.timezone(TIMEZONE)) > finish
        ):
            continue

        issue_data = IssueData(
            repository_name=repository.name,
            number=issue._id,
            title=issue.title,
            state=issue.state,
            task=issue.body,
            created_at=str(issue.created_at),
            creator_name=issue.user.username,
            creator_login=issue.user.login,
            creator_email=issue.user.email,
            closed_at=nvl(issue.closed_at),
            closer_name=issue.closed_by.username if issue.closed_by else None,
            closer_login=issue.closed_by.login if issue.closed_by else None,
            closer_email=issue.closed_by.email if issue.closed_by else None,
            assignee_story=get_assignee_story(issue),
            connected_pull_requests=(
                get_connected_pulls(issue._id, repository.owner, repository.name, token)
                if issue._id is not None
                else EMPTY_FIELD
            ),
            labels=';'.join(issue.labels) if issue.labels else EMPTY_FIELD,
            milestone=get_info(issue.milestone, 'title'),
        )

        comments = client.get_comments(repository, issue)
        log_issue_and_comments(csv_name, issue_data, comments)
        sleep(TIMEDELTA)


def log_issue_and_comments(csv_name, issue_data: IssueData, comments):
    if comments:
        for comment in comments:
            comment_data = IssueDataWithComment(
                **issue_data,
                body=comment.body,
                created_at=str(comment.created_at),
                author_name=comment.author.username,
                author_login=comment.author.login,
                author_email=comment.author.email,
            )
            comment_data = asdict(comment_data)

            logger.log_to_csv(csv_name, list(comment_data.keys()), comment_data)
            logger.log_to_stdout(comment_data)
    else:
        info = asdict(issue_data)
        logger.log_to_csv(csv_name, list(info.keys()), info)
        logger.log_to_stdout(info)


def log_issues(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    fork_flag: bool,
):
    info = asdict(IssueDataWithComment())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        try:
            logger.log_title(repo.name)
            log_repository_issues(client, repo, csv_name, token, start, finish)
            if fork_flag:
                forked_repos = client.get_forks(repo)
                for forked_repo in forked_repos:
                    logger.log_title("FORKED:", forked_repo.name)
                    log_repository_issues(
                        client, forked_repo, csv_name, token, start, finish
                    )
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print("log_issues exception:", e)
