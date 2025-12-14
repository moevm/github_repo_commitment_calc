from __future__ import annotations

from dataclasses import asdict, dataclass
from time import sleep
from typing import Generator

from src.constants import EMPTY_FIELD, TIMEDELTA
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger
from src.contributors_parser import ContributorData

from src.graphql.builder.models import Query, Field


def _nvl(val: str | None) -> str:
    return val or EMPTY_FIELD


def build_collaborators_query() -> Query:
    return Query(
        name="GetCollaborators",
        variables={
            "owner": "String!",
            "repo": "String!",
            "first": "Int!",
            "after": "String",
            "affiliation": "CollaboratorAffiliation",
        },
        fields=[
            Field(
                "repository",
                args={"owner": "$owner", "name": "$repo"},
                fields=[
                    "nameWithOwner",
                    Field(
                        "collaborators",
                        args={
                            "first": "$first",
                            "after": "$after",
                            "affiliation": "$affiliation",
                        },
                        fields=[
                            "totalCount",
                            Field("pageInfo", fields=["hasNextPage", "endCursor"]),
                            Field("edges", fields=["permission"]),
                            Field(
                                "nodes",
                                fields=[
                                    "login",
                                    "name",
                                    "email",
                                    "url",
                                    "bio",
                                    "isSiteAdmin",
                                    "id",
                                    "__typename",
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


def log_repository_contributors_by_graphql(
    owner: str,
    repo_name: str,
    token: str,
    csv_name: str,
    first_n: int = 100,
    affiliation: str = "ALL",
) -> None:
    query = build_collaborators_query()

    has_next_page = True
    after_cursor: str | None = None
    processed_count = 0

    while has_next_page:
        variables = {
            "owner": owner,
            "repo": repo_name,
            "first": first_n,
            "after": after_cursor,
            "affiliation": affiliation,
        }

        data = query.execute(
            variables=variables,
            token=token,
        )

        repo_data = data["repository"]
        collab_block = repo_data["collaborators"]

        page_info = collab_block["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        after_cursor = page_info["endCursor"]

        nodes = collab_block["nodes"]
        edges = collab_block["edges"] or []

        processed_count += len(nodes)
        logger.log_to_stdout(
            f"Processing collaborators {processed_count} / {collab_block['totalCount']}"
        )

        for idx, node in enumerate(nodes):
            edge = edges[idx] if idx < len(edges) else {}
            permission = edge.get("permission")

            contributor_data = ContributorData(
                repository_name=repo_data["nameWithOwner"],
                login=node["login"],
                name=_nvl(node.get("name")),
                email=_nvl(node.get("email")),
                url=node["url"],
                permissions=_nvl(permission),
                total_commits=0,               
                node_id=node.get("id") or "",
                type=node.get("__typename") or "",
                bio=_nvl(node.get("bio")),
                site_admin=bool(node.get("isSiteAdmin")),
            )

            info_dict = asdict(contributor_data)
            logger.log_to_csv(csv_name, list(info_dict.keys()), info_dict)
            logger.log_to_stdout(info_dict)

            sleep(TIMEDELTA)


def log_contributors_by_graphql(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str
) -> None:
    info = asdict(ContributorData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for _, repo, token in binded_repos:
        logger.log_title(repo.name)
        log_repository_contributors_by_graphql(
            owner=repo.owner.login,
            repo_name=repo.name,
            token=token,
            csv_name=csv_name
        )
        sleep(100 * TIMEDELTA)
