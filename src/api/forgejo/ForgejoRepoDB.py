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
from src.api.forgejo.sql_queries import GET_FULL_PR_INFO, GET_USER_BY_ID, GET_REPO


class ForgejoDBClient:
    def __init__(self, connect_info: dict):
        self.connection_params = dict(
            host=connect_info.get("FORGEJO_DB_HOST", 'db'),
            port=int(connect_info.get("FORGEJO_DB_PORT", 5432)),
            dbname=connect_info.get("FORGEJO_DB_NAME", 'forgejo'),
            user=connect_info.get("FORGEJO_DB_USER", "forgejo"),
            password=connect_info.get("FORGEJO_DB_PASSWORD", "moevmforgejopassword"),
        )
        self.connection = None
        self.base_url = connect_info.get("base_url")

    def __enter__(self):
        self.connection = psycopg2.connect(**self.connection_params)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and not self.connection.closed:
            self.connection.close()
        return False

    def get_all_pull_requests(self):
        with self:
            with self.connection.cursor() as cur:
                cur.execute(GET_FULL_PR_INFO)
                columns = [d[0] for d in cur.description]
                rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        logging.error(f"{rows}")
        return [self._row_to_pr(row) for row in rows]

    @staticmethod
    def _user_from_row(row: dict, prefix: str, base_url: str = "") -> User | None:
        uid = row.get(f"{prefix}_id")
        if not uid:
            return None

        login = row.get(f"{prefix}_login") or ""
        return User(
            _id=uid,
            login=login,
            username=row.get(f"{prefix}_full_name") or row.get(f"{prefix}_name") or "No name",
            email=row.get(f"{prefix}_email") or "",
            html_url=f"{base_url.rstrip('/')}/{login}" if base_url and login else "",
            node_id=str(uid),
            type={0: "User", 1: "Organization"}.get(row.get(f"{prefix}_type") or 0, ""),
            bio=row.get(f"{prefix}_bio") or "",
            site_admin=bool(row.get(f"{prefix}_is_admin")),
        )

    def _row_to_pr(self, row: dict) -> PullRequest:
        author = self._user_from_row(row, "creator", self.base_url)
        merged_by = (
            self._user_from_row(row, "merger", self.base_url)
            if row["merged"] else None
        )

        return PullRequest(
            _id=row["number"],
            title=row["title"],
            author=author,
            state=row["state"],
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

class ForgejoRepoDB():
    _USER_TYPES = {0: "User", 1: "Organization", 2: "Bot"}

    def __init__(self, client: ForgejoDBClient):
        self.client = client

    def get_user_data(self, row: dict) -> User:
        """
        row — dict w/keys: id, name, lower_name, full_name,
            email, description, is_admin, type.
        """
        login = row.get("lower_name") or row.get("name") or ""
        return User(
            login=login,
            username=row.get("full_name") or row.get("name") or "No name",
            email=row.get("email") or "",
            html_url=f"{self.client.base_url}/{login}" if self.client.base_url else None,
            node_id=row.get("id"),
            type=self._USER_TYPES.get(row.get("type") or 0, ""),
            bio=row.get("description") or "",
            site_admin=bool(row.get("is_admin")),
            _id=row.get("id"),
        )

    def get_user_by_id(self, user_id: int) -> User | None:
        with self.client:
            with self.client.connection.cursor() as cur:
                cur.execute(GET_USER_BY_ID, (user_id,))
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return self.get_user_data(dict(zip(cols, row)))

    @log_exceptions(default_return=None, message="Failed to get repository from Forgejo DB")
    def get_repository(self, id: str) -> Repository | None:
        logging.info(f"{self} doesn't support get_repository (it parses all PR in DB), so returned Repo is Mock")
        with self.client:
            with self.client.connection.cursor() as cur:
                cur.execute(GET_REPO, (id,))
                row = cur.fetchone()
                if not row:
                    logging.error(f"Repository {id} not found in Forgejo DB.")
                    return None
                cols = [d[0] for d in cur.description]
                row = dict(zip(cols, row))

        owner = self.get_user_data({
            "id": row["owner_id"],
            "name": row["owner_name_user"],
            "lower_name": row["owner_login"],
            "full_name": row["owner_full_name"],
            "email": row["owner_email"],
            "description": row["owner_description"],
            "is_admin": row["owner_is_admin"],
            "type": row["owner_type"],
        })

        return Repository(
            _id=f"{row['owner_name']}/{row['name']}",
            name=row["name"],
            url=f"{self.client.base_url}/{row['owner_name']}/{row['name']}" if self.client.base_url else None,
            default_branch=Branch(name=row["default_branch"], last_commit=None),
            owner=owner,
        )

    @log_exceptions(
        default_return=[], message="Failed to get all pull requests from Forgejo DB"
    )
    def get_pull_requests(self, repo: Repository) -> list[PullRequest]:
        logging.info(f"{self} doesn't support per-repo - it returns all PR in DB")
        return self.client.get_all_pull_requests()

    def get_rate_limiting(self) -> tuple[int, int]:
        import sys
        return sys.maxsize, sys.maxsize

    def get_base_url(self):
        return self.client.base_url