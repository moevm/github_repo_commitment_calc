from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from time import sleep
from typing import Generator

import pytz

from src.constants import EMPTY_FIELD, TIMEDELTA, TIMEZONE
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger
from src.issues_parser import IssueData

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


def build_issues_query() -> Query:
    return Query(
        name="GetIssues",
        variables={
            "owner": "String!",
            "repo": "String!",
            "first": "Int!",
            "after": "String",
            "since": "DateTime",
            "timelineFirst": "Int!",
        },
        fields=[
            Field(
                "repository",
                args={"owner": "$owner", "name": "$repo"},
                fields=[
                    "nameWithOwner",
                    Field(
                        "issues",
                        args={
                            "first": "$first",
                            "after": "$after",
                            "orderBy": {"field": "CREATED_AT", "direction": "DESC"},
                            "states": ["OPEN", "CLOSED"],
                            "filterBy": {"since": "$since"},
                        },
                        fields=[
                            "totalCount",
                            Field("pageInfo", fields=["hasNextPage", "endCursor"]),
                            Field(
                                "nodes",
                                fields=[
                                    "number",
                                    "title",
                                    "state",
                                    "body",
                                    "createdAt",
                                    "closedAt",
                                    Field(
                                        "author",
                                        fields=[
                                            "login",
                                            InlineFragment("User", fields=["name", "email"]),
                                        ],
                                    ),
                                    Field(
                                        "timelineItems",
                                        args={
                                            "first": "$timelineFirst",
                                            "itemTypes": ["CLOSED_EVENT", "CONNECTED_EVENT", "CROSS_REFERENCED_EVENT"],
                                        },
                                        fields=[
                                            Field(
                                                "nodes",
                                                fields=[
                                                    InlineFragment(
                                                        "ClosedEvent",
                                                        fields=[
                                                            "createdAt",
                                                            Field(
                                                                "actor",
                                                                fields=[
                                                                    "login",
                                                                    InlineFragment("User", fields=["name", "email"]),
                                                                ],
                                                            ),
                                                        ],
                                                    ),
                                                    InlineFragment(
                                                        "ConnectedEvent",
                                                        fields=[
                                                            Field(
                                                                "subject",
                                                                fields=[
                                                                    InlineFragment("PullRequest", fields=["url"]),
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                    InlineFragment(
                                                        "CrossReferencedEvent",
                                                        fields=[
                                                            Field(
                                                                "source",
                                                                fields=[
                                                                    InlineFragment("PullRequest", fields=["url"]),
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            )
                                        ],
                                    ),
                                    Field("labels", args={"first": 50}, fields=[Field("nodes", fields=["name"])]),
                                    Field("milestone", fields=["title"]),
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


def build_issue_comments_query() -> Query:
    return Query(
        name="GetIssueComments",
        variables={
            "owner": "String!",
            "repo": "String!",
            "number": "Int!",
            "first": "Int!",
            "after": "String",
        },
        fields=[
            Field(
                "repository",
                args={"owner": "$owner", "name": "$repo"},
                fields=[
                    Field(
                        "issue",
                        args={"number": "$number"},
                        fields=[
                            Field(
                                "comments",
                                args={"first": "$first", "after": "$after"},
                                fields=[
                                    "totalCount",
                                    Field("pageInfo", fields=["hasNextPage", "endCursor"]),
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
                        ],
                    )
                ],
            )
        ],
    )


def _extract_connected_prs(timeline_nodes: list[dict]) -> str:
    urls: list[str] = []
    for node in timeline_nodes:
        subject = node.get("subject") or {}
        pr_url = subject.get("url")
        if pr_url and pr_url not in urls:
            urls.append(pr_url)

        source = node.get("source") or {}
        pr_url = source.get("url")
        if pr_url and pr_url not in urls:
            urls.append(pr_url)

    return ";".join(urls) if urls else EMPTY_FIELD


def _log_issue_and_comments_by_graphql(
    owner: str,
    repo_name: str,
    token: str,
    csv_name: str,
    issue_data: IssueData,
    comments_first_n: int = 100,
) -> None:
    query = build_issue_comments_query()

    has_next_page = True
    after_cursor: str | None = None
    wrote_any = False

    while has_next_page:
        try:
            data = query.execute(
                variables={
                    "owner": owner,
                    "repo": repo_name,
                    "number": issue_data.number,
                    "first": comments_first_n,
                    "after": after_cursor,
                },
                token=token,
            )
        except RuntimeError as exc:
            logger.log_error(f"GraphQL comments failed for issue #{issue_data.number}: {exc}")
            break

        issue = (data.get("repository") or {}).get("issue") or {}
        comments_block = issue.get("comments") or {}

        page_info = comments_block.get("pageInfo") or {}
        has_next_page = bool(page_info.get("hasNextPage"))
        after_cursor = page_info.get("endCursor")

        nodes = comments_block.get("nodes") or []
        for comment in nodes:
            wrote_any = True
            author = comment.get("author") or {}

            row = IssueData(
                **(
                    asdict(issue_data)
                    | dict(
                        comment_body=comment.get("body") or "",
                        comment_created_at=comment.get("createdAt") or "",
                        comment_author_name=_nvl(author.get("name")),
                        comment_author_login=_nvl(author.get("login")),
                        comment_author_email=_nvl(author.get("email")),
                    )
                )
            )
            row_dict = asdict(row)
            logger.log_to_csv(csv_name, list(row_dict.keys()), row_dict)
            logger.log_to_stdout(row_dict)
            sleep(TIMEDELTA)

    if not wrote_any:
        info = asdict(issue_data)
        logger.log_to_csv(csv_name, list(info.keys()), info)
        logger.log_to_stdout(info)


def log_repository_issues_by_graphql(
    owner: str,
    repo_name: str,
    token: str,
    csv_name: str,
    start: datetime,
    finish: datetime,
    first_n: int = 50,
    timeline_first_n: int = 50,
) -> None:
    query = build_issues_query()

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
            "since": start.astimezone(pytz.UTC).isoformat(),
            "timelineFirst": timeline_first_n,
        }

        try:
            data = query.execute(variables=variables, token=token)
        except RuntimeError as exc:
            logger.log_error(f"GraphQL request failed: {exc}")
            logger.log_to_stdout(f"Sleep to {100 * TIMEDELTA} and retry")
            sleep(100 * TIMEDELTA)
            continue

        repo_data = data["repository"]
        issues_block = repo_data["issues"]

        page_info = issues_block["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        after_cursor = page_info["endCursor"]

        nodes = issues_block["nodes"] or []
        processed_count += len(nodes)
        logger.log_to_stdout(f"Processing issues {processed_count} / {issues_block['totalCount']}")

        for issue in nodes:
            created_at_str = issue.get("createdAt") or ""
            created_local = _parse_iso_to_tz(created_at_str, TIMEZONE)

            if created_local < start.astimezone(tz) or created_local > finish.astimezone(tz):
                continue

            author = issue.get("author") or {}

            closer = {}
            timeline_nodes = ((issue.get("timelineItems") or {}).get("nodes") or [])
            for node in timeline_nodes:
                if node.get("actor"):
                    closer = node.get("actor") or {}
                    break

            labels_nodes = (issue.get("labels") or {}).get("nodes") or []
            labels_str = ";".join(lbl.get("name") for lbl in labels_nodes if lbl.get("name")) or EMPTY_FIELD
            milestone = (issue.get("milestone") or {}).get("title") or EMPTY_FIELD
            connected_prs = _extract_connected_prs(timeline_nodes)

            issue_data = IssueData(
                repository_name=repo_data["nameWithOwner"],
                number=int(issue["number"]),
                title=issue.get("title") or "",
                state=str(issue.get("state") or "").lower(),
                task=issue.get("body") or "",
                created_at=created_at_str,
                creator_name=_nvl(author.get("name")),
                creator_login=_nvl(author.get("login")),
                creator_email=_nvl(author.get("email")),
                closed_at=issue.get("closedAt"),
                closer_name=closer.get("name"),
                closer_login=closer.get("login"),
                closer_email=closer.get("email"),
                assignee_story=EMPTY_FIELD,
                connected_pull_requests=connected_prs,
                labels=labels_str,
                milestone=milestone,
            )

            _log_issue_and_comments_by_graphql(
                owner=owner,
                repo_name=repo_name,
                token=token,
                csv_name=csv_name,
                issue_data=issue_data,
            )
            sleep(TIMEDELTA)


def log_issues_by_graphql(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    forks_include: bool = False,
) -> None:
    info = asdict(IssueData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        repositories = [repo]
        if forks_include:
            repositories.extend(client.get_forks(repo))

        for current_repo in repositories:
            title = current_repo.name if current_repo._id == repo._id else f"FORKED: {current_repo.name}"
            logger.log_title(title)
            log_repository_issues_by_graphql(
                owner=current_repo.owner.login,
                repo_name=current_repo.name,
                token=token,
                csv_name=csv_name,
                start=start,
                finish=finish,
            )
            sleep(100 * TIMEDELTA)
