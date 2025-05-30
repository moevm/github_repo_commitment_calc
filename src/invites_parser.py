from dataclasses import asdict, dataclass
from time import sleep
from typing import Generator

from src.constants import TIMEDELTA
from src.interface_wrapper import IRepositoryAPI, Repository
from src.utils import logger


@dataclass(kw_only=True, frozen=True)
class InviteData:
    repository_name: str = ''
    invited_login: str = ''
    invite_creation_date: str = ''
    invitation_url: str = ''


def log_repository_invitations(
    client: IRepositoryAPI, repository: Repository, csv_name: str
):
    invitations = client.get_invites(repository)
    for invite in invitations:
        invite_data = InviteData(
            repository_name=repository.name,
            invited_login=invite.invitee.login,
            invite_creation_date=invite.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
            invitation_url=invite.html_url,
        )
        invite_dict = asdict(invite_data)
        logger.log_to_csv(csv_name, list(invite_dict.keys()), invite_dict)
        logger.log_to_stdout(invite_dict)
        sleep(TIMEDELTA)


def log_invitations(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
):
    info = asdict(InviteData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        print(client, repo, token)
        logger.log_title(repo.name)
        log_repository_invitations(client, repo, csv_name)
