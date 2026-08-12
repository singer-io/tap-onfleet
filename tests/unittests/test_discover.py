"""Unit tests for tap_onfleet.discover module."""
import importlib
import unittest
from unittest.mock import MagicMock, patch

from tap_onfleet.discover import _apply_access_checks, discover_streams
from tap_onfleet.exceptions import OnfleetForbiddenError
from tap_onfleet.streams import STREAMS

discover_module = importlib.import_module('tap_onfleet.discover')


class TestDiscoverStreams(unittest.TestCase):

    def test_get_abs_path_resolves_within_module_dir(self):
        """get_abs_path builds paths relative to discover module file."""
        result = discover_module.get_abs_path('schemas/administrators.json')
        self.assertTrue(result.endswith('tap_onfleet/schemas/administrators.json'))

    def test_returns_all_streams(self):
        """discover_streams returns an entry for every stream in STREAMS."""
        client = MagicMock()
        result = discover_streams(client)
        self.assertEqual(len(result), len(STREAMS))

    def test_entries_have_required_keys(self):
        """Each discover entry has stream, tap_stream_id, schema, metadata."""
        client = MagicMock()
        result = discover_streams(client)
        for entry in result:
            with self.subTest(stream=entry['stream']):
                self.assertIn('stream', entry)
                self.assertIn('tap_stream_id', entry)
                self.assertIn('schema', entry)
                self.assertIn('metadata', entry)

    def test_stream_names_match(self):
        """stream and tap_stream_id match the expected names."""
        client = MagicMock()
        result = discover_streams(client)
        names = {e['stream'] for e in result}
        self.assertEqual(names, set(STREAMS.keys()))

    def test_schema_properties_present(self):
        """Each stream's schema has properties."""
        client = MagicMock()
        result = discover_streams(client)
        for entry in result:
            with self.subTest(stream=entry['stream']):
                self.assertIn('properties', entry['schema'])
                self.assertGreater(len(entry['schema']['properties']), 0)

    def test_logs_warning_for_excluded_streams(self):
        """Excluded streams log the expected unauthorized warning."""
        class NoAccessStream:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return False

        class AccessibleStream:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return True

        fake_streams = {
            'blocked': NoAccessStream,
            'allowed': AccessibleStream,
        }
        schemas = {'blocked': {}, 'allowed': {}}
        field_metadata = {'blocked': [], 'allowed': []}

        with patch('tap_onfleet.discover.STREAMS', fake_streams):
            with patch('tap_onfleet.discover.logger.warning') as warning_mock:
                _apply_access_checks(MagicMock(), schemas, field_metadata)

        warning_mock.assert_called_once_with(
            'Unauthorized streams excluded from catalog: %s',
            'blocked',
        )

    def test_raises_forbidden_when_no_streams_accessible(self):
        """No accessible streams raises forbidden error with exact message."""
        class NoAccessStream:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return False

        fake_streams = {
            'blocked_a': NoAccessStream,
            'blocked_b': NoAccessStream,
        }
        schemas = {'blocked_a': {}, 'blocked_b': {}}
        field_metadata = {'blocked_a': [], 'blocked_b': []}

        with patch('tap_onfleet.discover.STREAMS', fake_streams):
            with self.assertRaisesRegex(
                OnfleetForbiddenError,
                'No streams are accessible. Ensure the credentials have read permission for at least one stream.',
            ) as err:
                _apply_access_checks(MagicMock(), schemas, field_metadata)

        self.assertEqual(
            str(err.exception),
            'No streams are accessible. Ensure the credentials have read permission for at least one stream.',
        )
