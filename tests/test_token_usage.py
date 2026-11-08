import unittest
from unittest.mock import Mock, patch

from src.git_logger import Clients
from src.api.github.GitHubRepoAPI import GitHubRepoAPI
from src.api.utils import APITypes


class TestTokenUsage(unittest.TestCase):
    def test_client_validation_does_not_require_user_token(self):
        client = Mock()
        self.assertIs(GitHubRepoAPI(client).client, client)
        client.get_rate_limit.assert_called_once_with()
        client.get_user.assert_not_called()

    def test_failed_client_validation(self):
        client = Mock()
        client.get_rate_limit.side_effect = RuntimeError("invalid token")
        with self.assertLogs(level="ERROR"):
            self.assertIsNone(GitHubRepoAPI(client).client)

    @patch("src.git_logger.sleep")
    @patch("src.git_logger.RepositoryFactory.create_api")
    def test_selects_client_by_current_remaining_limit(self, create_api, sleep):
        first, second = Mock(), Mock()
        create_api.side_effect = [(first, "first-token"), (second, "second-token")]
        clients = Clients(APITypes.github, [dict(token="first-token"), dict(token="second-token")])
        for limits, expected in (
            ((100, 200), (second, "second-token")),
            ((200, 100), (first, "first-token")),
            ((100, 100), (first, "first-token")),
            ((0, 1), (second, "second-token")),
        ):
            with self.subTest(limits=limits):
                first.get_rate_limiting.return_value = (limits[0], 5000)
                second.get_rate_limiting.return_value = (limits[1], 5000)
                self.assertEqual(clients.get_next_client(), expected)

    @patch("src.git_logger.RepositoryFactory.create_api", return_value=(None, None))
    def test_no_valid_clients(self, create_api):
        with self.assertRaisesRegex(Exception, "No clients after login"):
            Clients(APITypes.github, [dict(token="invalid")])


if __name__ == "__main__":
    unittest.main()
