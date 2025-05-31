import argparse
import sys
import unittest

from unittest_parametrize import ParametrizedTestCase, param, parametrize

import git_logger
from main import run


def parse_args(args):
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

    return parser.parse_args(args)


class TestTokenUsage(ParametrizedTestCase):
    def setUp(self):
        test_args = parse_args(sys.argv[1:])
        self.tokens = [test_args.tt1, test_args.tt2]
        self.repo = test_args.repo
        self.output_csv = test_args.out

        self.args = argparse.Namespace(
            commits=False,
            issues=False,
            pull_requests=False,
            wikis=False,
            contributors=False,
            invites=False,
            workflow_runs=False,
            start="2000/01/01-00:00:00",
            finish="2400/01/01-00:00:00",
            branch="default",
            forks_include=False,
            pr_comments=False,
            export_google_sheets=False,
            out=test_args.out,
        )

    @staticmethod
    def _get_rate_limit(clients: git_logger.Clients):
        return [client.get_rate_limiting()[0] for client in clients.clients]

    @staticmethod
    def _is_only_one_token_used(limit_start, limit_finish):
        return bool(limit_start[0] - limit_finish[0]) != bool(
            limit_start[1] - limit_finish[1]
        )

    @staticmethod
    def _is_max_token_used(limit_start, limit_finish):
        if limit_start[0] - limit_finish[0]:
            return limit_start[0] == max(limit_start)
        else:
            return limit_start[1] == max(limit_start)

    @staticmethod
    def _change_tokens_order(tokens, key):
        key %= len(tokens)
        return tokens[key:] + tokens[:key]

    def _get_usage(self, binded_repos, clients):
        limit_start = self._get_rate_limit(clients)

        run(self.args, binded_repos)

        limit_finish = self._get_rate_limit(clients)

        return limit_start, limit_finish

    @parametrize(
        'args',
        [
            param({'commits': True}, id='commits'),
            param({'contributors': True}, id='contributors'),
            param({'issues': True}, id='issues'),
            param({'invites': True}, id='invites'),
            param({'pull_requests': True}, id='pull_requests'),
            param({'workflow_runs': True}, id='workflow_runs'),
        ],
    )
    def test_commits_parser(self, args: dict[str, bool]):
        # patch args
        for k, v in args.items():
            setattr(self.args, k, v)

        for i in range(2):
            clients = git_logger.Clients(
                self._change_tokens_order(self.tokens, i)
            )
            binded_repos = git_logger.get_next_binded_repo(clients, [self.repo])

            limit_start, limit_finish = self._get_usage(binded_repos, clients)

            self.assertTrue(self._is_only_one_token_used(limit_start, limit_finish))
            self.assertTrue(self._is_max_token_used(limit_start, limit_finish))


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
