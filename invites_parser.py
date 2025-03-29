from dataclasses import asdict, dataclass
from time import sleep

from constants import TIMEDELTA
from interface_wrapper import IRepositoryAPI, Repository
from utils import logger


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


def log_invitations(client: IRepositoryAPI, working_repos, csv_name: str):
    info = asdict(InviteData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for repo, token in working_repos:
        logger.log_title(repo.name)
        try:
            log_repository_invitations(client, repo, csv_name)
        except Exception as e:
            print(e)
