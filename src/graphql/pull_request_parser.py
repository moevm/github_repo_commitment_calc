from dataclasses import asdict
from typing import Generator
from time import sleep

import requests

from src.constants import TIMEDELTA
from src.repo_dataclasses import PullRequestData
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger


# -----------GraphQLAPI block--------------

def log_repositories_pr_by_graphql(owner, repo_name, token, csv_name, first_n=100):
    HEADERS = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    query = """
    query GetPRData($owner: String!, $repo: String!, $first: Int!, $after: String) {
        repository(owner: $owner, name: $repo) {
            nameWithOwner
            pullRequests(first: $first, after: $after, states: [OPEN, CLOSED, MERGED], orderBy: {field: CREATED_AT, direction: DESC}) {
                totalCount
                pageInfo {		
                    hasNextPage		
                    endCursor		
                }
                nodes {
                    title
                    number
                    state
                    createdAt
                
                    author {
                        login
                        ... on User {
                        name
                        email
                        }
                    }
                
                    baseRef {
                        name
                        target {
                        oid
                        }
                    }

                    headRef {
                        name
                        target {
                        oid
                        }
                    }
                
                    changedFiles
                    additions
                    deletions
                
                    mergedAt
                    mergedBy {
                        login
                        ... on User {
                        name
                        email
                        }
                    }
                    
                    assignees(first: 10) {
                        nodes {
                        login
                        name
                        }
                    }
                    
                    labels(first: 20) {
                        nodes {
                        name
                        color
                        }
                    }
                }
            }
        }
    }
    """

    has_next_page = True
    after_cursor = None
    processed_count = 0

    while has_next_page:

        variables = {
            "owner": owner,
            "repo": repo_name,
            "first": first_n,
            "after": after_cursor,
        }

        response = requests.post(
            "https://api.github.com/graphql",
            headers=HEADERS,
            json={"query": query, "variables": variables},
        )

        if response.status_code != 200:
            raise Exception(f"Query failed: {response.status_code} - {response.text}")

        graphql_data = response.json()

        if "errors" in graphql_data:
            raise Exception(f"GraphQL errors: {graphql_data['errors']}")

        page_info = repo_data["pullRequests"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        after_cursor = page_info["endCursor"]

        repo_data = graphql_data["data"]["repository"]
        prs = repo_data["pullRequests"]["nodes"]

        processed_count += len(prs)
        logger.log_to_stdout(f"Processing {processed_count} / {repo_data["pullRequests"]['totalCount']}")

        for pr in prs:
            pr_data = PullRequestData(
                repository_name=repo_data["nameWithOwner"],
                title=pr["title"],
                id=pr["number"],
                state=str(pr["state"]).lower(),
                commit_into=(
                    pr["baseRef"]["target"]["oid"]
                    if pr["baseRef"] and pr["baseRef"]["target"]
                    else None
                ),
                commit_from=(
                    pr["headRef"]["target"]["oid"]
                    if pr["headRef"] and pr["headRef"]["target"]
                    else None
                ),
                created_at=pr["createdAt"],
                creator_name=(
                    pr["author"]["name"]
                    if pr["author"] and "name" in pr["author"]
                    else None
                ),
                creator_login=pr["author"]["login"] if pr["author"] else None,
                creator_email=(
                    pr["author"]["email"]
                    if pr["author"] and "email" in pr["author"]
                    else None
                ),
                changed_files=pr["changedFiles"],
                comment_body=None,
                comment_created_at=None,
                comment_author_name=None,
                comment_author_login=None,
                comment_author_email=None,
                merger_name=(
                    pr["mergedBy"]["name"]
                    if pr["mergedBy"] and "name" in pr["mergedBy"]
                    else None
                ),
                merger_login=pr["mergedBy"]["login"] if pr["mergedBy"] else None,
                merger_email=(
                    pr["mergedBy"]["email"]
                    if pr["mergedBy"] and "email" in pr["mergedBy"]
                    else None
                ),
                source_branch=pr["headRef"]["name"] if pr["headRef"] else None,
                target_branch=pr["baseRef"]["name"] if pr["baseRef"] else None,
                assignee_story=None,
                related_issues=None,
                labels=", ".join([label["name"] for label in pr["labels"]["nodes"]]),
                milestone=None,
            )

            pr_info = asdict(pr_data)
            logger.log_to_csv(csv_name, list(pr_info.keys()), pr_info)
            logger.log_to_stdout(pr_info)
        sleep(TIMEDELTA)


def log_pull_requests_by_graphql(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
):
    info = asdict(PullRequestData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for _, repo, token in binded_repos:
        logger.log_title(repo.name)
        log_repositories_pr_by_graphql(
            owner=repo.owner.login, repo_name=repo.name, csv_name=csv_name, token=token
        )
        sleep(TIMEDELTA)
