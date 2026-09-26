import base64
import logging

import psycopg2


from src.api.baseAPI import IRepositoryAPI
from src.api.models import (
    Branch,
    Comment,
    Commit,
    Contributor,
    Issue,
    PullRequest,
    Repository,
    User,
    WikiPage,
)
from src.utils import log_exceptions
from src.api.forgejo.sql_queries import GET_FULL_PR_INFO


class ForgejoDBClient:
    def __init__(self, connect_info: dict):
        self.connection_params = dict(
            host=connect_info.get("FORGEJO_DB_HOST"),
            port=int(connect_info.get("FORGEJO_DB_PORT", 5432)),
            dbname=connect_info.get("FORGEJO_DB_NAME"),
            user=connect_info.get("FORGEJO_DB_USER"),
            password=connect_info.get("FORGEJO_DB_PASSWORD"),
        )
        self.connection = psycopg2.connect(**self.connection_params)

    def __enter__(self):
        self.connection = psycopg2.connect(**self.connection_params)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and not self.connection.closed:
            self.connection.close()
        return False

    def get_all_pull_requests(self):
        with self.connection.cursor() as cur:
            cur.execute(GET_FULL_PR_INFO, ([], ))
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]

        return [self._row_to_pr(row) for row in rows]

    @staticmethod
    def _row_to_pr(row: dict) -> PullRequest:
        author = User(
            name=row["creator_name"],
            login=row["creator_login"],
            email=row["creator_email"],
        )

        merged_by = None
        if row["merged"] and row["merger_login"]:
            merged_by = User(
                name=row["merger_name"],
                login=row["merger_login"],
                email=row["merger_email"],
            )

        return PullRequest(
            _id=row["number"],                      # per-repo номер PR (GitHub API: p.number)
            title=row["title"],
            author=author,
            state=row["state"],                     # 'open' / 'closed'
            created_at=row["created_at"],
            head_label=row["source_branch"],
            base_label=row["target_branch"],
            head_ref=row["source_branch"],
            base_ref=row["target_branch"],
            merged_by=merged_by,
            merged=bool(row["merged"]),
            files=[],
            issue_url=None,
            labels=row["labels"].split(", ") if row["labels"] else [],
            milestone=row["milestone"],
            comments=row["num_comments"] or 0,
            review_comments=0,
        )

class ForgejoRepoDB(IRepositoryAPI):
    def __init__(self, client: ForgejoDBClient):
        self.client = client

    @log_exceptions(
        default_return=[], message="Failed to get all pull requests from Forgejo DB"
    )
    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
        logging.info(f"{self} doesn't support per-repo - it returns all PR in DB")
        return self.client.get_all_pull_requests()
