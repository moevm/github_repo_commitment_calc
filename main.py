import argparse
from datetime import datetime
import pytz

import git_logger
import export_sheets
import commits_parser
import pull_requests_parser
import issues_parser
import invites_parser
import wikipars
import contributors_parser


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--invites", help="print pending invites", action="store_true")
    parser.add_argument("-c", "--commits", help="log commits", action="store_true")
    parser.add_argument(
        "-p", "--pull_requests", help="log pull requests", action="store_true"
    )
    parser.add_argument("-i", "--issues", help="log issues", action="store_true")
    parser.add_argument("-w", "--wikis", help="log wikis", action="store_true")
    parser.add_argument("--contributors", help="log contributors", action="store_true")
    parser.add_argument(
        "--forks_include", help="logging data from forks", action="store_true"
    )
    parser.add_argument(
        "-e",
        "--export_google_sheets",
        help="export table to google sheets",
        action="store_true",
    )
    parser.add_argument(
        '-t', '--token', type=str, required=True, help='token github account'
    )
    parser.add_argument(
        '-l',
        '--list',
        type=str,
        required=True,
        help='Path to the file containing the list of repositories. Repositories should be separated by a line break. Names should be in the format <organization or owner>/<name> ',
    )
    parser.add_argument(
        "--download_repos",
        type=str,
        help="path to downloaded repositories",
        default='./',
    )
    parser.add_argument('-o', '--out', type=str, required=True, help='output filename')
    parser.add_argument(
        "--pr_comments", help="log comments for PR", action="store_true"
    )
    parser.add_argument(
        '-s',
        '--start',
        type=str,
        required=False,
        help='start time',
        default='2000/01/01-00:00:00',
    )
    parser.add_argument(
        '-f',
        '--finish',
        type=str,
        required=False,
        help='finish time',
        default='2400/01/01-00:00:00',
    )
    parser.add_argument(
        '-b',
        '--branch',
        type=str,
        required=False,
        help='branch to select commits, by default use "default" repository branch, use "all" to get all commits from all branches',
        default=None,
    )
    parser.add_argument(
        '--google_token',
        type=str,
        required=False,
        help='Specify path to google token file',
    )
    parser.add_argument(
        '--table_id',
        type=str,
        required=False,
        help='Specify Google sheet document id (can find in url)',
    )
    parser.add_argument(
        '--sheet_id',
        type=str,
        required=False,
        help='Specify title for a sheet in a document in which data will be printed',
    )
    args = parser.parse_args()

    if args.export_google_sheets:
        for action in parser._actions:
            if action.dest == 'google_token':
                action.required = True
            if action.dest == 'table_id':
                action.required = True
            if action.dest == 'sheet_id':
                action.required = True
    return parser.parse_args()


def parse_time(datetime_str):
    start = (
        datetime_str[0].split('/') + datetime_str[1].split(':')
        if len(datetime_str) == 2
        else datetime_str[0].split('/') + ['00', '00', '00']
    )
    start = [int(i) for i in start]
    start_datetime = datetime(
        year=start[0],
        month=start[1],
        day=start[2],
        hour=start[3],
        minute=start[4],
        second=start[5],
    )
    return start_datetime.astimezone(pytz.timezone(git_logger.TIMEZONE))


def main():
    args = parse_args()
    token = args.token
    repositories = args.list
    csv_name = args.out
    path_drepo = args.download_repos
    fork_flag = args.forks_include
    log_pr_comments = args.pr_comments

    try:
        client = git_logger.login(token=token)
    except Exception as e:
        print(e)
    else:
        working_repos = git_logger.get_next_repo(client, repositories)
        start = parse_time(args.start.split('-'))
        finish = parse_time(args.finish.split('-'))

        if args.commits:
            commits_parser.log_commits(
                client, working_repos, csv_name, start, finish, args.branch, fork_flag
            )
        if args.pull_requests:
            pull_requests_parser.log_pull_requests(
                client,
                working_repos,
                csv_name,
                token,
                start,
                finish,
                fork_flag,
                log_pr_comments,
            )
        if args.issues:
            issues_parser.log_issues(
                client, working_repos, csv_name, token, start, finish, fork_flag
            )
        if args.invites:
            invites_parser.log_invitations(client, working_repos, csv_name)
        if args.wikis:
            wikipars.wikiparser(client, repositories, path_drepo, csv_name)
        if args.contributors:
            contributors_parser.log_contributors(
                client, working_repos, csv_name, fork_flag
            )
        if args.export_google_sheets:
            export_sheets.write_data_to_table(
                csv_name, args.google_token, args.table_id, args.sheet_id
            )


if __name__ == '__main__':
    main()
