"""Unit tests for tap_onfleet.discover module."""
import unittest
from unittest.mock import MagicMock, patch

from tap_onfleet.discover import _apply_access_checks, discover_streams
from tap_onfleet.exceptions import OnfleetForbiddenError
from tap_onfleet.streams import STREAMS


class TestDiscoverStreams(unittest.TestCase):

    @staticmethod
    def _get_warning_payload(warning_mock):
        for call in warning_mock.call_args_list:
            args = call[0]
            if args and args[0] == 'Unauthorized streams excluded from catalog: %s':
                return args[1]
        return None

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

    def test_logs_warning_for_inaccessible_streams(self):
        """Inaccessible streams are excluded with the expected warning."""
        client = MagicMock()
        stream_names = list(STREAMS.keys())
        inaccessible_stream = stream_names[0]

        with patch('tap_onfleet.discover.LOGGER.warning') as warning_mock:
            with patch.object(STREAMS[inaccessible_stream], 'check_access', return_value=False):
                result = _apply_access_checks(client, stream_names)

        self.assertNotIn(inaccessible_stream, result)
        warning_mock.assert_any_call(
            'Unauthorized streams excluded from catalog: %s',
            inaccessible_stream,
        )

    def test_raises_forbidden_with_expected_message_when_no_stream_access(self):
        """No accessible streams raises forbidden error with expected message."""
        class NoAccessStreamA:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return False

        class NoAccessStreamB:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return False

        fake_streams = {
            'stream_a': NoAccessStreamA,
            'stream_b': NoAccessStreamB,
        }

        client = MagicMock()
        with patch('tap_onfleet.discover.STREAMS', fake_streams):
            with self.assertRaisesRegex(
                OnfleetForbiddenError,
                'No streams are accessible. Ensure the credentials have read permission for at least one stream.',
            ) as err:
                _apply_access_checks(client, list(fake_streams.keys()))

        self.assertEqual(
            str(err.exception),
            'No streams are accessible. Ensure the credentials have read permission for at least one stream.',
        )

    def test_logs_warning_includes_child_pruned_streams(self):
        """Summary warning includes child streams removed due to inaccessible parent."""
        class ParentStream:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return False

        class ChildStream:
            parent = 'parent'

            def __init__(self, client=None):
                del client

            def check_access(self):
                return True

        class IndependentStream:
            parent = None

            def __init__(self, client=None):
                del client

            def check_access(self):
                return True

        fake_streams = {
            'parent': ParentStream,
            'child': ChildStream,
            'independent': IndependentStream,
        }

        client = MagicMock()
        with patch('tap_onfleet.discover.STREAMS', fake_streams):
            with patch('tap_onfleet.discover.LOGGER.warning') as warning_mock:
                result = _apply_access_checks(client, list(fake_streams.keys()))

        self.assertNotIn('parent', result)
        self.assertNotIn('child', result)
        self.assertIn('independent', result)

        warning_payload = self._get_warning_payload(warning_mock)
        self.assertIsNotNone(warning_payload)
        excluded_streams = set(warning_payload.split(', '))
        self.assertEqual(excluded_streams, {'parent', 'child'})
