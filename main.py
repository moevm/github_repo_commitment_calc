import argparse
import traceback

import git_logger
import export_sheets
import commits_parser
import contributors_parser
import pull_requests_parser
import invites_parser
import issues_parser
import wikipars

from utils import parse_time


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

    token = parser.add_mutually_exclusive_group(required=True)
    token.add_argument('-t', '--token', type=str, help='account access token')
    token.add_argument('--tokens', type=str, help='path to your tokens')

    parser.add_argument(
        '-l',
        '--list',
        type=str,
        required=True,
        help=(
            'Path to the file containing the list of repositories. '
            'Repositories should be separated by a line break. '
            'Names should be in the format <organization or owner>/<name> '
        ),
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
        help=(
            'branch to select commits, '
            'by default use "default" repository branch, '
            'use "all" to get all commits from all branches',
        ),
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


def run(args, binded_repos, repos_for_wiki=None):
    start = parse_time(args.start.split('-'))
    finish = parse_time(args.finish.split('-'))

    if args.commits:
        commits_parser.log_commits(
            binded_repos, args.out, start, finish, args.branch, args.forks_include
        )
    if args.pull_requests:
        pull_requests_parser.log_pull_requests(
            binded_repos,
            args.out,
            start,
            finish,
            args.forks_include,
            args.pr_comments,
        )
    if args.issues:
        issues_parser.log_issues(
            binded_repos, args.out, start, finish, args.forks_include
        )
    if args.invites:
        invites_parser.log_invitations(
            binded_repos,
            args.out,
        )
    if args.contributors:
        contributors_parser.log_contributors(binded_repos, args.out, args.forks_include)
    if args.wikis:
        wikipars.wiki_parser(repos_for_wiki, args.download_repos, args.out)
    if args.export_google_sheets:
        export_sheets.write_data_to_table(
            args.out, args.google_token, args.table_id, args.sheet_id
        )


def main():
    args = parse_args()

    if args.token:
        tokens = [args.token]
    else:
        tokens = git_logger.get_tokens_from_file(args.tokens)

    repositories = git_logger.get_repos_from_file(args.list)

    print(repositories)

    try:
        clients = git_logger.Clients("github", tokens)
        binded_repos = git_logger.get_next_binded_repo(clients, repositories)
    except Exception as e:
        print(e)
        print(traceback.print_exc())
    else:
        run(args, binded_repos)


if __name__ == '__main__':
    main()
