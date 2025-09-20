import argparse
import traceback
import sys

from src import commits_parser
from src import contributors_parser
from src import export_sheets
from src import git_logger
from src import invites_parser
from src import issues_parser
from src import pull_requests_parser
from src import wikipars
from src import workflow_runs_parser
from src.utils import parse_time, validate_and_normalize_cell


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
        "--workflow_runs", help="log workflow runs", action="store_true"
    )
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
        '--start_cell',
        type=str,
        required=False,
        help='Starting cell for Google Sheets export (e.g., "A1", "B3")',
        default="A1"
    )

    parser.add_argument(
        '--base_url',
        type=str,
        required=False,
        help='Base URL for Forgejo instance (if using Forgejo)',
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
        '--sheet_name',
        type=str,
        required=False,
        help='Specify title for a sheet in a document in which data will be printed',
    )
    parser.add_argument(
        "--clear_sheet",
        action="store_true",
        required=False,
        help="Specify to clear sheet content before printing",
    )
    args = parser.parse_args()

    if args.export_google_sheets:
        for action in parser._actions:
            if action.dest == 'google_token':
                action.required = True
            if action.dest == 'table_id':
                action.required = True
            if action.dest == 'sheet_name':
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
            binded_repos, args.out, start, finish, args.forks_include, args.base_url,
        )
    if args.invites:
        invites_parser.log_invitations(
            binded_repos,
            args.out,
        )
    if args.contributors:
        contributors_parser.log_contributors(binded_repos, args.out, args.forks_include)
    if args.workflow_runs:
        workflow_runs_parser.log_workflow_runs(
            binded_repos, args.out, args.forks_include
        )
    if args.wikis:
        wikipars.wikiparser(repos_for_wiki, args.download_repos, args.out)
    if args.export_google_sheets:
        export_sheets.write_data_to_table(
            csv_path=args.out,
            google_token=args.google_token,
            table_id=args.table_id,
            sheet_name=args.sheet_name,
            start_cell=args.start_cell,
            clear_content=args.clear_sheet,
        )


def main():
    args = parse_args()

    try:
        args.start_cell = validate_and_normalize_cell(args.start_cell)
    except ValueError as e:
        print(f"Error in start_cell argument: {e}")
        sys.exit(1)

    if args.token:
        tokens = [args.token]
    else:
        tokens = git_logger.get_tokens_from_file(args.tokens)

    repositories = git_logger.get_repos_from_file(args.list)

    try:
        clients = git_logger.Clients(tokens, args.base_url)
        binded_repos = git_logger.get_next_binded_repo(clients, repositories)
    except Exception as e:
        print(f"Failed to initialize any clients: {e}")
        print(traceback.format_exc())
        return

    run(args, binded_repos, repositories)


if __name__ == '__main__':
    main()
