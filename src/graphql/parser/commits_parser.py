from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from time import sleep
from typing import Generator

import pytz

from src.constants import EMPTY_FIELD, GOOGLE_MAX_CELL_LEN, TIMEDELTA, TIMEZONE
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger
from src.commits_parser import CommitData

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


def build_branches_query() -> Query:
    return Query(
        name="GetBranches",
        variables={"owner": "String!", "repo": "String!", "first": "Int!", "after": "String"},
        fields=[
            Field(
                "repository",
                args={"owner": "$owner", "name": "$repo"},
                fields=[
                    Field(
                        "refs",
                        args={
                            "refPrefix": "refs/heads/",
                            "first": "$first",
                            "after": "$after",
                        },
                        fields=[
                            "totalCount",
                            Field("pageInfo", fields=["hasNextPage", "endCursor"]),
                            Field("nodes", fields=["name"]),
                        ],
                    )
                ],
            )
        ],
    )


def build_commits_history_query() -> Query:
    return Query(
        name="GetCommitsByBranch",
        variables={
            "owner": "String!",
            "repo": "String!",
            "refName": "String!",
            "first": "Int!",
            "after": "String",
            "since": "GitTimestamp",
            "until": "GitTimestamp",
        },
        fields=[
            Field(
                "repository",
                args={"owner": "$owner", "name": "$repo"},
                fields=[
                    "nameWithOwner",
                    Field(
                        "ref",
                        args={"qualifiedName": "$refName"},
                        fields=[
                            "name",
                            Field(
                                "target",
                                fields=[
                                    InlineFragment(
                                        "Commit",
                                        fields=[
                                            Field(
                                                "history",
                                                args={
                                                    "first": "$first",
                                                    "after": "$after",
                                                    "since": "$since",
                                                    "until": "$until",
                                                },
                                                fields=[
                                                    "totalCount",
                                                    Field("pageInfo", fields=["hasNextPage", "endCursor"]),
                                                    Field(
                                                        "nodes",
                                                        fields=[
                                                            "oid",
                                                            "committedDate",
                                                            "additions",
                                                            "deletions",
                                                            "changedFiles",
                                                            Field(
                                                                "author",
                                                                fields=[
                                                                    "name",
                                                                    "email",
                                                                    Field(
                                                                        "user",
                                                                        fields=[
                                                                            "login",
                                                                            "name",
                                                                            "email",
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
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


def _get_branches_by_graphql(owner: str, repo_name: str, token: str, first_n: int = 100) -> list[str]:
    query = build_branches_query()

    has_next_page = True
    after_cursor: str | None = None
    branches: list[str] = []

    while has_next_page:
        data = query.execute(
            variables={"owner": owner, "repo": repo_name, "first": first_n, "after": after_cursor},
            token=token,
        )

        refs_block = (data.get("repository") or {}).get("refs") or {}
        page_info = refs_block.get("pageInfo") or {}
        has_next_page = bool(page_info.get("hasNextPage"))
        after_cursor = page_info.get("endCursor")

        nodes = refs_block.get("nodes") or []
        for node in nodes:
            name = node.get("name")
            if name:
                branches.append(name)

        sleep(TIMEDELTA)

    return branches


def log_repository_commits_by_graphql(
    owner: str,
    repo_name: str,
    token: str,
    csv_name: str,
    start: datetime,
    finish: datetime,
    branch: str | None,
    commits_first_n: int = 100,
) -> None:
    branches: list[str] = []
    match branch:
        case "all":
            try:
                branches = _get_branches_by_graphql(owner, repo_name, token)
            except RuntimeError as exc:
                logger.log_error(f"GraphQL branches failed: {exc}")
                branches = []
        case None:
            branches = ["main"]
        case _:
            branches = [branch]

    commits_query = build_commits_history_query()

    for br in branches:
        logger.log_to_stdout(f"Processing branch {br}")

        has_next_page = True
        after_cursor: str | None = None

        while has_next_page:
            ref_name = f"refs/heads/{br}"

            try:
                data = commits_query.execute(
                    variables={
                        "owner": owner,
                        "repo": repo_name,
                        "refName": ref_name,
                        "first": commits_first_n,
                        "after": after_cursor,
                        "since": start.astimezone(pytz.UTC).isoformat(),
                        "until": finish.astimezone(pytz.UTC).isoformat(),
                    },
                    token=token,
                )
            except RuntimeError as exc:
                logger.log_error(f"GraphQL commits failed for {ref_name}: {exc}")
                logger.log_to_stdout(f"Sleep to {100 * TIMEDELTA} and retry")
                sleep(100 * TIMEDELTA)
                continue

            repo_data = data.get("repository") or {}
            ref_data = repo_data.get("ref") or {}
            if not ref_data:
                logger.log_error(f"Ref not found or no access: {ref_name}")
                break

            target = ref_data.get("target") or {}
            history = (target.get("history") or {}) if isinstance(target, dict) else {}
            page_info = history.get("pageInfo") or {}

            has_next_page = bool(page_info.get("hasNextPage"))
            after_cursor = page_info.get("endCursor")

            nodes = history.get("nodes") or []
            for commit in nodes:
                committed_at_str = commit.get("committedDate") or ""
                committed_local = _parse_iso_to_tz(committed_at_str, TIMEZONE)

                if committed_local < start or committed_local > finish:
                    continue

                author = commit.get("author") or {}
                user = author.get("user") or {}

                changed_files_value = EMPTY_FIELD
                if commit.get("changedFiles") is not None:
                    changed_files_value = str(commit.get("changedFiles"))
                changed_files_value = (changed_files_value or "")[:GOOGLE_MAX_CELL_LEN]

                commit_data = CommitData(
                    repository_name=repo_data.get("nameWithOwner") or f"{owner}/{repo_name}",
                    author_name=_nvl(user.get("name") or author.get("name")),
                    author_login=_nvl(user.get("login")),
                    author_email=_nvl(user.get("email") or author.get("email")),
                    date_and_time=committed_local.isoformat(),
                    changed_files=changed_files_value,
                    commit_id=commit.get("oid") or "",
                    branch=br,
                    additions=str(commit.get("additions") or ""),
                    deletions=str(commit.get("deletions") or ""),
                )

                info = asdict(commit_data)
                logger.log_to_csv(csv_name, list(info.keys()), info)
                logger.log_to_stdout(info)
                sleep(TIMEDELTA)

        sleep(TIMEDELTA)


def log_commits_by_graphql(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    start: datetime,
    finish: datetime,
    branch: str | None,
    forks_include: bool = False,
) -> None:
    info = asdict(CommitData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        repositories = [repo]
        if forks_include:
            repositories.extend(client.get_forks(repo))

        for current_repo in repositories:
            title = current_repo.name if current_repo._id == repo._id else f"FORKED: {current_repo.name}"
            logger.log_title(title)
            log_repository_commits_by_graphql(
                owner=current_repo.owner.login,
                repo_name=current_repo.name,
                token=token,
                csv_name=csv_name,
                start=start,
                finish=finish,
                branch=branch,
            )
            sleep(100 * TIMEDELTA)
