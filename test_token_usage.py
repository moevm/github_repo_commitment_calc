import unittest
import argparse
import sys
from utils import parse_time
from datetime import datetime
from interface_wrapper import RepositoryFactory, IRepositoryAPI

import git_logger

from repo_parser import (
    commits_parser,
    contributors_parser,
    pull_requests_parser,
    invites_parser,
    issues_parser,
    wiki_parser,
)


def fix_rate_limit(clients: git_logger.Clients):
    return [c['client'].get_rate_limiting() for c in clients.clients]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tt1', type=str, required=True, help='first test token')
    parser.add_argument('--tt2', type=str, required=True, help='second test token')

    parser.add_argument(
        '-r',
        '--repo',
        type=str,
        required=True,
        help=('test repo'),
    )

    parser.add_argument('-o', '--out', type=str, required=True, help='output filename')

    return parser.parse_args()


class TestCommitsParser(unittest.TestCase):
    def setUp(self):
        args = parse_args()
        print(args)

        self.token1 = args.tt1
        self.token2 = args.tt2
        self.repo = args.test_repo
        self.output_csv = args.out

        self.start = parse_time('2000/01/01-00:00:00')
        self.finish = parse_time('2400/01/01-00:00:00')
        self.branch = 'default'
        self.fork_flag = False

    def test_commits_parser(self):
        clients1 = git_logger.Clients("github", [self.token1, self.token2])
        binded_repos1 = git_logger.get_next_binded_repo(clients1, [self.test_repo])

        rate_limit_start = fix_rate_limit(clients1)

        commits_parser.log_commits(
            binded_repos1,
            self.output_csv,
            self.start,
            self.finish,
            self.branch,
            self.fork_flag,
        )

        rate_limit_finish = fix_rate_limit(clients1)

        print(rate_limit_start, rate_limit_finish)

        pass


if __name__ == '__main__':
    unittest.main()
