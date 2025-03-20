from utils import logger
from time import sleep
from github import Github, Repository, GithubException, PullRequest

FIELDNAMES = (
    'repository name',
    'invited login',
    'invite creation date',
    'invitation url',
)
TIMEDELTA = 0.05

def log_inviter(repo, invite, writer):
    invite_info = [
        repo.full_name,
        invite.invitee.login,
        invite.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
        invite.html_url,
    ]
    writer.writerow(invite_info)
    print(invite_info)

def log_repository_invitations(repository: Repository, csv_name):
    invitations = repository.get_pending_invitations()
    for invite in invitations:
        invite_info = {
        'repository name': repository.full_name,
        'invited login': invite.invitee.login,
        'invite creation date': invite.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
        'invitation url': invite.html_url,
        }
        logger.log_to_csv(csv_name, FIELDNAMES, invite_info)
        logger.log_to_stdout(invite_info)
        sleep(TIMEDELTA)


def log_invitations(client: Github, working_repos, csv_name):
    logger.log_to_csv(csv_name, FIELDNAMES)

    for repo in working_repos:
        logger.log_title(repo.full_name)
        try:
            log_repository_invitations(repo, csv_name)
        except Exception as e:
            print(e)
