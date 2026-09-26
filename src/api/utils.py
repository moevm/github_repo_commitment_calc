from enum import StrEnum


class APITypes(StrEnum):
    forgejo = "forgejo"
    forgejo_db = "forgejo_db"
    github = "github"
