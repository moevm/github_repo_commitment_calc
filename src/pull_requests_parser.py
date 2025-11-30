import json
from dataclasses import asdict, dataclass
from datetime import datetime
from time import sleep
from typing import Generator

import pytz
import requests

from src.constants import EMPTY_FIELD, TIMEDELTA, TIMEZONE
from src.git_logger import get_assignee_story
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger
from src.graphql.pull_request_parser import log_pull_requests_by_graphql    # for using in main.py
from src.repo_dataclasses import PullRequestData


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


def nvl(val):
    return val or EMPTY_FIELD


def get_info(obj, attr):
    return EMPTY_FIELD if obj is None else getattr(obj, attr)


# -----------GithubAPI block--------------


def log_repositories_pr(
    client: IRepositoryAPI,
    repository: Repository,
    csv_name,
    token,
    start,
    finish,
    log_comments=False,
):
    def nvl(val):
        return val or EMPTY_FIELD

    def get_info(obj, attr):
        return EMPTY_FIELD if obj is None else getattr(obj, attr)

    pulls = client.get_pull_requests(repository)
    for pull in pulls:
        if (
            pull.created_at.astimezone(pytz.timezone(TIMEZONE)) < start
            or pull.created_at.astimezone(pytz.timezone(TIMEZONE)) > finish
        ):
            continue

        pr_data = PullRequestData(
            repository_name=repository.name,
            title=pull.title,
            id=pull._id,
            state=pull.state,
            commit_into=pull.base_label,
            commit_from=pull.head_label,
            created_at=str(pull.created_at),
            creator_name=nvl(pull.author.username),
            creator_login=pull.author.login,
            creator_email=pull.author.email,
            changed_files='; '.join(pull.files),
            merger_name=pull.merged_by.username if pull.merged_by else None,
            merger_login=pull.merged_by.login if pull.merged_by else None,
            merger_email=pull.merged_by.email if pull.merged_by else None,
            source_branch=pull.head_ref,
            target_branch=pull.base_ref,
            assignee_story=get_assignee_story(pull, client, token, repository),
            related_issues=(
                get_related_issues(pull._id, repository.owner, repository.name, token)
                if pull.issue_url is not None
                else EMPTY_FIELD
            ),
            labels=';'.join(pull.labels) if pull.labels else EMPTY_FIELD,
            milestone=pull.milestone,
        )

        if log_comments:
            comments = client.get_comments(repository, pull)
            if comments:
                for comment in comments:
                    comment_data = PullRequestData(
                        **(
                            asdict(pr_data) |
                            dict(
                                comment_body=comment.body,
                                comment_created_at=str(comment.created_at),
                                comment_author_name=comment.author.name,
                                comment_author_login=comment.author.login,
                                comment_author_email=nvl(comment.author.email),
                            )
                        )
                    )
                    comment_data = asdict(comment_data)

                    logger.log_to_csv(csv_name, list(comment_data.keys()), comment_data)
                    logger.log_to_stdout(comment_data)
            else:
                base_pr_info = asdict(pr_data)
                logger.log_to_csv(csv_name, list(base_pr_info.keys()), base_pr_info)
                logger.log_to_stdout(base_pr_info)
        else:
            base_pr_info = asdict(pr_data)
            logger.log_to_csv(csv_name, list(base_pr_info.keys()), base_pr_info)
            logger.log_to_stdout(base_pr_info)

        sleep(TIMEDELTA)


def log_pull_requests(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    fork_flag: bool,
    log_comments=False,
):
    info = asdict(PullRequestData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        logger.log_title(repo.name)
        log_repositories_pr(
            client, repo, csv_name, token, start, finish, log_comments
        )
        if fork_flag:
            forked_repos = client.get_repo(repo._id).get_forks()
            for forked_repo in forked_repos:
                logger.log_title(f"FORKED: {forked_repo.name}")
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
