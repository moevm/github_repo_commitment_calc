from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from time import sleep
from typing import Generator

import pytz

from src.constants import EMPTY_FIELD, TIMEDELTA, TIMEZONE
from src.repo_dataclasses import PullRequestData
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger

from src.graphql.builder.models import Query, Field, InlineFragment


def _nvl(val: str | None) -> str:
    return val or EMPTY_FIELD


def _parse_iso_to_tz(dt_str: str, tz_name: str) -> datetime:
    if not dt_str:
        return datetime.min.replace(tzinfo=pytz.UTC)

    if dt_str.endswith("Z"):
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(dt_str)

    tz = pytz.timezone(tz_name)
    return dt.astimezone(tz)


def build_pull_requests_query(include_comments: bool = False) -> Query:
    pr_fields = [
        "title",
        "number",
        "state",
        "createdAt",
        Field(
            "author",
            fields=[
                "login",
                InlineFragment("User", fields=["name", "email"]),
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
                InlineFragment("User", fields=["name", "email"]),
            ],
        ),
        Field(
            "assignees",
            args={"first": 10},
            fields=[Field("nodes", fields=["login", "name"])],
        ),
        Field(
            "labels",
            args={"first": 20},
            fields=[Field("nodes", fields=["name", "color"])],
        ),
        Field(
            "closingIssuesReferences",
            args={"first": 50},
            fields=[Field("nodes", fields=["url"])],
        ),
    ]

    if include_comments:
        pr_fields.append(
            Field(
                "comments",
                args={"first": 100},
                fields=[
                    "totalCount",
                    Field(
                        "nodes",
                        fields=[
                            "body",
                            "createdAt",
                            Field(
                                "author",
                                fields=[
                                    "login",
                                    InlineFragment("User", fields=["name", "email"]),
                                ],
                            ),
                        ],
                    ),
                ],
            )
        )

    return Query(
        name="GetPRData",
        variables={"owner": "String!", "repo": "String!", "first": "Int!", "after": "String"},
        fields=[
            Field(
                "repository",
                args={"owner": "$owner", "name": "$repo"},
                fields=[
                    "nameWithOwner",
                    Field(
                        "pullRequests",
                        args={
                            "first": "$first",
                            "after": "$after",
                            "states": ["OPEN", "CLOSED", "MERGED"],
                            "orderBy": {"field": "CREATED_AT", "direction": "DESC"},
                        },
                        fields=[
                            "totalCount",
                            Field("pageInfo", fields=["hasNextPage", "endCursor"]),
                            Field("nodes", fields=pr_fields),
                        ],
                    ),
                ],
            )
        ],
    )


def _get_related_issues(pr: dict) -> str:
    nodes = (pr.get("closingIssuesReferences") or {}).get("nodes") or []
    urls = [node.get("url") for node in nodes if node.get("url")]
    return ";".join(urls) if urls else EMPTY_FIELD


def _build_rows_from_pr(repo_name: str, pr: dict, include_comments: bool) -> list[PullRequestData]:
    author = pr.get("author") or {}
    merged_by = pr.get("mergedBy") or {}
    base_ref = pr.get("baseRef") or {}
    head_ref = pr.get("headRef") or {}
    base_target = base_ref.get("target") or {}
    head_target = head_ref.get("target") or {}

    labels_nodes = (pr.get("labels") or {}).get("nodes") or []
    labels_str = ", ".join(label.get("name") for label in labels_nodes if label.get("name")) or EMPTY_FIELD

    base_row = PullRequestData(
        repository_name=repo_name,
        title=pr.get("title") or "",
        id=int(pr.get("number") or 0),
        state=str(pr.get("state") or "").lower(),
        commit_into=base_target.get("oid") or EMPTY_FIELD,
        commit_from=head_target.get("oid") or EMPTY_FIELD,
        created_at=pr.get("createdAt") or "",
        creator_name=_nvl(author.get("name")),
        creator_login=_nvl(author.get("login")),
        creator_email=_nvl(author.get("email")),
        changed_files=str(pr.get("changedFiles") or EMPTY_FIELD),
        comment_body="",
        comment_created_at="",
        comment_author_name="",
        comment_author_login="",
        comment_author_email="",
        merger_name=merged_by.get("name"),
        merger_login=merged_by.get("login"),
        merger_email=merged_by.get("email"),
        source_branch=head_ref.get("name") or EMPTY_FIELD,
        target_branch=base_ref.get("name") or EMPTY_FIELD,
        assignee_story=EMPTY_FIELD,
        related_issues=_get_related_issues(pr),
        labels=labels_str,
        milestone=EMPTY_FIELD,
    )

    if not include_comments:
        return [base_row]

    comments = (pr.get("comments") or {}).get("nodes") or []
    if not comments:
        return [base_row]

    rows: list[PullRequestData] = []
    for comment in comments:
        comment_author = comment.get("author") or {}
        rows.append(
            PullRequestData(
                **(
                    asdict(base_row)
                    | dict(
                        comment_body=comment.get("body") or "",
                        comment_created_at=comment.get("createdAt") or "",
                        comment_author_name=_nvl(comment_author.get("name")),
                        comment_author_login=_nvl(comment_author.get("login")),
                        comment_author_email=_nvl(comment_author.get("email")),
                    )
                )
            )
        )

    return rows


def log_repositories_pr_by_graphql(
    owner: str,
    repo_name: str,
    token: str,
    csv_name: str,
    start: datetime,
    finish: datetime,
    pr_comments: bool = False,
    first_n: int = 100,
) -> None:
    query = build_pull_requests_query(include_comments=pr_comments)

    has_next_page = True
    after_cursor: str | None = None
    processed_count = 0
    tz = pytz.timezone(TIMEZONE)

    while has_next_page:
        variables = {
            "owner": owner,
            "repo": repo_name,
            "first": first_n,
            "after": after_cursor,
        }

        try:
            graphql_data = query.execute(variables=variables, token=token)
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

        prs = pr_block["nodes"] or []
        processed_count += len(prs)
        logger.log_to_stdout(f"Processing {processed_count} / {pr_block['totalCount']}")

        for pr in prs:
            created_local = _parse_iso_to_tz(pr.get("createdAt") or "", TIMEZONE)
            if created_local < start.astimezone(tz) or created_local > finish.astimezone(tz):
                continue

            rows = _build_rows_from_pr(repo_data["nameWithOwner"], pr, include_comments=pr_comments)
            for row in rows:
                pr_info = asdict(row)
                logger.log_to_csv(csv_name, list(pr_info.keys()), pr_info)
                logger.log_to_stdout(pr_info)
                sleep(TIMEDELTA)


def log_pull_requests_by_graphql(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    forks_include: bool = False,
    pr_comments: bool = False,
) -> None:
    info = asdict(PullRequestData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        repositories = [repo]
        if forks_include:
            repositories.extend(client.get_forks(repo))

        for current_repo in repositories:
            title = current_repo.name if current_repo._id == repo._id else f"FORKED: {current_repo.name}"
            logger.log_title(title)
            log_repositories_pr_by_graphql(
                owner=current_repo.owner.login,
                repo_name=current_repo.name,
                csv_name=csv_name,
                token=token,
                start=start,
                finish=finish,
                pr_comments=pr_comments,
            )
            sleep(100 * TIMEDELTA)
