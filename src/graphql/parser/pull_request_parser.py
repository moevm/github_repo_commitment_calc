from __future__ import annotations

from dataclasses import asdict
from typing import Generator
from time import sleep

from src.constants import TIMEDELTA
from src.repo_dataclasses import PullRequestData
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger

from src.graphql.builder.models import Query, Field, InlineFragment


def build_pull_requests_query() -> Query:
    """Строит GraphQL-запрос к GitHub для получения PR."""
    return Query(
        name="GetPRData",
        variables={"owner": "String!", "repo": "String!", "first": "Int!", "after": "String"},
        fields=[
            Field("repository", args={"owner": "$owner", "name": "$repo"},
                fields=[
                    "nameWithOwner",
                    Field(
                        "pullRequests",
                        args={
                            "first": "$first",
                            "after": "$after",
                            "states": ["OPEN", "CLOSED", "MERGED"],
                            "orderBy": {
                                "field": "CREATED_AT",
                                "direction": "DESC",
                            },
                        },
                        fields=[
                            "totalCount",
                            Field("pageInfo", fields=["hasNextPage", "endCursor"]),
                            Field(
                                "nodes",
                                fields=[
                                    "title",
                                    "number",
                                    "state",
                                    "createdAt",
                                    Field(
                                        "author",
                                        fields=[
                                            "login",
                                            InlineFragment(
                                                "User",
                                                fields=["name", "email"],
                                            ),
                                        ],
                                    ),
                                    Field(
                                        "baseRef",
                                        fields=[
                                            "name",
                                            Field("target", fields=["oid"]),
                                        ],
                                    ),
                                    Field(
                                        "headRef",
                                        fields=[
                                            "name",
                                            Field("target", fields=["oid"]),
                                        ],
                                    ),
                                    "changedFiles",
                                    "additions",
                                    "deletions",
                                    "mergedAt",
                                    Field(
                                        "mergedBy",
                                        fields=[
                                            "login",
                                            InlineFragment(
                                                "User",
                                                fields=["name", "email"],
                                            ),
                                        ],
                                    ),
                                    Field(
                                        "assignees",
                                        args={"first": 10},
                                        fields=[
                                            Field(
                                                "nodes",
                                                fields=["login", "name"],
                                            )
                                        ],
                                    ),
                                    Field(
                                        "labels",
                                        args={"first": 20},
                                        fields=[
                                            Field(
                                                "nodes",
                                                fields=["name", "color"],
                                            )
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


def log_repositories_pr_by_graphql(owner: str, repo_name: str, token: str, csv_name: str, first_n: int = 100,) -> None:
    query = build_pull_requests_query()

    has_next_page = True
    after_cursor: str | None = None
    processed_count = 0

    while has_next_page:
        variables = {
            "owner": owner,
            "repo": repo_name,
            "first": first_n,
            "after": after_cursor,
        }

        try:
            graphql_data = query.execute(
                variables=variables,
                token=token,
            )
        except RuntimeError as exc:
            logger.log_error(f"GraphQL request failed: {exc}")
            logger.log_to_stdout(f"Sleep to {100 * TIMEDELTA} and retry")
            sleep(100 * TIMEDELTA)
            continue

        repo_data = graphql_data["repository"]
        pr_block = repo_data["pullRequests"]

        page_info = pr_block["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        after_cursor = page_info["endCursor"]

        prs = pr_block["nodes"]

        processed_count += len(prs)
        logger.log_to_stdout(
            f"Processing {processed_count} / {pr_block['totalCount']}"
        )

        for pr in prs:
            author = pr.get("author") or {}
            merged_by = pr.get("mergedBy") or {}
            base_ref = pr.get("baseRef") or {}
            head_ref = pr.get("headRef") or {}

            base_target = base_ref.get("target") or {}
            head_target = head_ref.get("target") or {}

            labels_nodes = (pr.get("labels") or {}).get("nodes") or []
            labels_str = ", ".join(label["name"] for label in labels_nodes)

            pr_data = PullRequestData(
                repository_name=repo_data["nameWithOwner"],
                title=pr["title"],
                id=pr["number"],
                state=str(pr["state"]).lower(),
                commit_into=(
                    base_target.get("oid")
                ),
                commit_from=(
                    head_target.get("oid")
                ),
                created_at=pr["createdAt"],
                creator_name=author.get("name"),
                creator_login=author.get("login"),
                creator_email=author.get("email"),
                changed_files=pr["changedFiles"],
                comment_body=None,
                comment_created_at=None,
                comment_author_name=None,
                comment_author_login=None,
                comment_author_email=None,
                merger_name=merged_by.get("name"),
                merger_login=merged_by.get("login"),
                merger_email=merged_by.get("email"),
                source_branch=head_ref.get("name"),
                target_branch=base_ref.get("name"),
                assignee_story=None,
                related_issues=None,
                labels=labels_str,
                milestone=None,
            )

            pr_info = asdict(pr_data)
            logger.log_to_csv(csv_name, list(pr_info.keys()), pr_info)
            logger.log_to_stdout(pr_info)


def log_pull_requests_by_graphql(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
) -> None:
    info = asdict(PullRequestData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for _, repo, token in binded_repos:
        logger.log_title(repo.name)
        log_repositories_pr_by_graphql(
            owner=repo.owner.login,
            repo_name=repo.name,
            csv_name=csv_name,
            token=token,
        )
        sleep(100 * TIMEDELTA)

