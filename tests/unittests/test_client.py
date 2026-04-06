"""Unit tests for tap_onfleet.onfleet (API client) module."""
import unittest
from unittest.mock import patch, MagicMock
from tap_onfleet.onfleet import Onfleet


class TestOnfleetInit(unittest.TestCase):
    """Tests for Onfleet constructor."""

    def test_default_init(self):
        client = Onfleet(
            start_date="2019-01-01T00:00:00Z",
            user_agent="test",
            api_key="key123",
            quota_limit=50,
        )
        self.assertEqual(client.uri, "https://onfleet.com/api/v2/")
        self.assertEqual(client.api_key, "key123")
        self.assertEqual(client.quota_limit, 50)


class TestEpochConversions(unittest.TestCase):
    """Tests for epoch ↔ datetime string conversions."""

    def setUp(self):
        self.client = Onfleet(
            start_date="2019-01-01T00:00:00Z",
            user_agent="test",
            api_key="key123",
        )

    def test_epoch_to_datetime_string(self):
        """Epoch millis are converted to a human-readable datetime string."""
        result = self.client._epoch_to_datetime_string(1551126790000)
        self.assertIsNotNone(result)
        self.assertIn('2019', result)

    def test_epoch_to_datetime_string_none(self):
        """None input returns None."""
        result = self.client._epoch_to_datetime_string(None)
        self.assertIsNone(result)

    def test_datetime_string_to_epoch(self):
        """A datetime string is converted back to epoch millis."""
        epoch = self.client._datetime_string_to_epoch("2019-02-25T20:13:10Z")
        self.assertIsInstance(epoch, float)
        self.assertGreater(epoch, 0)

    def test_dictionary_epoch_to_datetime_string(self):
        """datetime keys in a dict are converted from epoch to string."""
        d = {'timeCreated': 1551126790000, 'name': 'test'}
        result = self.client._dictionary_epoch_to_datetime_string(d)
        self.assertIn('2019', result['timeCreated'])
        self.assertEqual(result['name'], 'test')

    def test_dictionary_nested_conversion(self):
        """Nested dicts have their datetime fields converted."""
        d = {
            'completionDetails': {
                'time': 1551126790000,
                'failureReason': 'none',
            },
            'id': 'task1',
        }
        result = self.client._dictionary_epoch_to_datetime_string(d)
        self.assertIn('2019', result['completionDetails']['time'])

    def test_list_epoch_to_datetime_string(self):
        """List items (dicts) have their datetime fields converted."""
        lst = [
            {'timeCreated': 1551126790000, 'id': '1'},
            {'timeCreated': 1551126790000, 'id': '2'},
        ]
        result = self.client._list_epoch_to_datetime_string(lst)
        self.assertEqual(len(result), 2)
        self.assertIn('2019', result[0]['timeCreated'])


class TestCheckRateLimit(unittest.TestCase):
    """Tests for _check_rate_limit."""

    def setUp(self):
        self.client = Onfleet(
            start_date="2019-01-01T00:00:00Z",
            user_agent="test",
            api_key="key123",
            quota_limit=50,
        )

    @patch('tap_onfleet.onfleet.time.sleep')
    def test_rate_limit_triggers_sleep(self, mock_sleep):
        """When remaining is below quota threshold, sleep is called."""
        self.client._check_rate_limit(rate_limit_remaining='5',
                                       rate_limit_limit='100')
        mock_sleep.assert_called_once()

    @patch('tap_onfleet.onfleet.time.sleep')
    def test_rate_limit_no_sleep(self, mock_sleep):
        """When remaining is above threshold, no sleep."""
        self.client._check_rate_limit(rate_limit_remaining='90',
                                       rate_limit_limit='100')
        mock_sleep.assert_not_called()


class TestGet(unittest.TestCase):
    """Tests for the _get HTTP method."""

    def setUp(self):
        self.client = Onfleet(
            start_date="2019-01-01T00:00:00Z",
            user_agent="test",
            api_key="key123",
        )

    @patch('tap_onfleet.onfleet.requests.get')
    def test_get_calls_correct_url(self, mock_get):
        """_get builds the correct URL and calls requests.get."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }
        mock_get.return_value = mock_response

        self.client._get("admins", "2019-01-01T00:00:00Z")
        call_args = mock_get.call_args
        self.assertIn("admins", call_args[0][0])

    @patch('tap_onfleet.onfleet.requests.get')
    def test_get_passes_from_param(self, mock_get):
        """_get passes the 'from' date parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }
        mock_get.return_value = mock_response

        self.client._get("admins", "2019-01-01T00:00:00Z")
        call_args = mock_get.call_args
        self.assertIn('from', call_args[1].get('params', {}))

    @patch('tap_onfleet.onfleet.requests.get')
    def test_get_passes_lastId(self, mock_get):
        """_get includes lastId in params when provided."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }
        mock_get.return_value = mock_response

        self.client._get("tasks/all", "2019-01-01T00:00:00Z",
                         lastId="abc123")
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]['params']['lastId'], 'abc123')


class TestStreamEndpoints(unittest.TestCase):
    """Tests for the per-stream client methods (administrators, etc.)."""

    @patch('tap_onfleet.onfleet.requests.get')
    def test_administrators_returns_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'a1', 'timeCreated': 1551126790000,
             'timeLastModified': 1551126790000}
        ]
        mock_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }
        mock_get.return_value = mock_response

        client = Onfleet(start_date="2019-01-01T00:00:00Z",
                         user_agent="test", api_key="key123")
        result = client.administrators(bookmark="2019-01-01T00:00:00Z")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    @patch('tap_onfleet.onfleet.requests.get')
    def test_organizations_yields_records(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'org1', 'timeCreated': 1551126790000,
            'timeLastModified': 1551126790000, 'name': 'TestOrg',
        }
        mock_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }
        mock_get.return_value = mock_response

        client = Onfleet(start_date="2019-01-01T00:00:00Z",
                         user_agent="test", api_key="key123")
        result = list(client.organizations(bookmark="2019-01-01T00:00:00Z"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'org1')

    @patch('tap_onfleet.onfleet.requests.get')
    def test_tasks_yields_paginated(self, mock_get):
        """tasks() paginates via lastId and yields all records."""
        page1_response = MagicMock()
        page1_response.json.return_value = {
            'tasks': [
                {'id': 't1', 'timeCreated': 1551126790000,
                 'timeLastModified': 1551126790000},
            ],
            'lastId': 't1',
        }
        page1_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }

        page2_response = MagicMock()
        page2_response.json.return_value = {
            'tasks': [
                {'id': 't2', 'timeCreated': 1551126790000,
                 'timeLastModified': 1551126790000},
            ],
        }
        page2_response.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '100',
        }

        mock_get.side_effect = [page1_response, page2_response]

        client = Onfleet(start_date="2019-01-01T00:00:00Z",
                         user_agent="test", api_key="key123")
        result = list(client.tasks(bookmark="2019-01-01T00:00:00Z"))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 't1')
        self.assertEqual(result[1]['id'], 't2')
