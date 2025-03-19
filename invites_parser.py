import csv
import pytz
import requests
import json
from time import sleep
from github import Github, Repository, GithubException, PullRequest
import csv

FIELDNAMES = (
    'repository name',
    'invited login',
    'invite creation date',
    'invitation url',
)


def log_inviter(repo, invite, writer):
    invite_info = [
        repo.full_name,
        invite.invitee.login,
        invite.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
        invite.html_url,
    ]
    writer.writerow(invite_info)
    print(invite_info)


def log_invitations(client: Github, working_repos, csv_name, timedelta=1):
    with open(csv_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(FIELDNAMES)
        for repo in working_repos:
            print('=' * 20, repo.full_name, '=' * 20)
            invitations = repo.get_pending_invitations()
            for invite in invitations:
                try:
                    log_inviter(repo, invite, writer)
                    sleep(timedelta)
                except Exception as e:
                    print(e)
