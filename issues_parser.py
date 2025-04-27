import json
from dataclasses import asdict, dataclass
from datetime import datetime
from time import sleep
from typing import Generator
import os
from typing import Optional
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
    comment_body: str = ''
    comment_created_at: str = ''
    comment_author_name: str = ''
    comment_author_login: str = ''
    comment_author_email: str = ''


def get_connected_pulls(
    issue_number: int,
    repo_owner: str,
    repo_name: str,
    forgejo_token: Optional[str] = None
) -> str:

    base_url = os.getenv('FORGEJO_BASE_URL')
    if not base_url:
        raise ValueError("FORGEJO_BASE_URL environment variable must be set")
    
    token = forgejo_token or os.getenv('FORGEJO_TOKEN')
    if not token:
        raise ValueError(
            "Forgejo API token is required. "
            "Set FORGEJO_TOKEN environment variable or pass forgejo_token parameter"
        )
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/json"
    }
    
    connected_prs = set()
    api_base = f"{base_url}/api/v1/repos/{repo_owner}/{repo_name}"
    
    try:
        comments_response = requests.get(
            f"{api_base}/issues/{issue_number}/comments",
            headers=headers
        )
        comments_response.raise_for_status()
        
        for comment in comments_response.json():
            body = comment.get("body", "")
            if not body:
                continue
                
            for word in body.split():
                clean_word = word.strip(".,:;!?()[]{}")
                if len(clean_word) > 1 and clean_word[1:].isdigit():
                    if clean_word.startswith('#'):  
                        pr_num = clean_word[1:]
                        connected_prs.add(f"{base_url}/{repo_owner}/{repo_name}/pulls/{pr_num}")
                    elif clean_word.startswith('!'):  
                        pr_num = clean_word[1:]
                        connected_prs.add(f"{base_url}/{repo_owner}/{repo_name}/pulls/{pr_num}")

        prs_response = requests.get(
            f"{api_base}/pulls?state=all",
            headers=headers
        )
        prs_response.raise_for_status()
        
        for pr in prs_response.json():
            if f"#{issue_number}" in pr.get("body", ""):
                connected_prs.add(pr.get("html_url"))
                
    except requests.exceptions.RequestException as e:
        print(f"[Warning] Failed to fetch connected PRs: {str(e)}")
        return 'Empty field'
    
    return ';'.join(sorted(connected_prs)) if connected_prs else 'Empty field'



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
            milestone=issue.milestone,
        )

        comments = client.get_comments(repository, issue)
        log_issue_and_comments(csv_name, issue_data, comments)
        sleep(TIMEDELTA)


def log_issue_and_comments(csv_name, issue_data: IssueData, comments):
    if comments:
        for comment in comments:
            comment_data = IssueDataWithComment(
                **asdict(issue_data),
                comment_body=comment.body,
                comment_created_at=str(comment.created_at),
                comment_author_name=comment.author.username,
                comment_author_login=comment.author.login,
                comment_author_email=comment.author.email,
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
                    logger.log_title(f"FORKED: {forked_repo.name}")
                    log_repository_issues(
                        client, forked_repo, csv_name, token, start, finish
                    )
                    sleep(TIMEDELTA)
            sleep(TIMEDELTA)
        except Exception as e:
            print("log_issues exception:", e)
            exit(1)
