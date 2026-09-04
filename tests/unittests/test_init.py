"""Unit tests for tap_onfleet.__init__ module."""
import unittest
from unittest.mock import MagicMock, patch

from singer import metadata, Catalog

import tap_onfleet
from tap_onfleet import discover, get_selected_streams, main, stream_is_selected, sync
from tap_onfleet.discover import discover_streams


class TestStreamIsSelected(unittest.TestCase):

    def test_selected_true(self):
        mdata = {(): {'selected': True}}
        self.assertTrue(stream_is_selected(mdata))

    def test_selected_false(self):
        mdata = {(): {'selected': False}}
        self.assertFalse(stream_is_selected(mdata))

    def test_selected_missing(self):
        mdata = {(): {}}
        self.assertFalse(stream_is_selected(mdata))


class TestGetSelectedStreams(unittest.TestCase):

    def test_returns_selected_only(self):
        """get_selected_streams returns only streams with selected=True."""
        client = MagicMock()
        raw = discover_streams(client)
        catalog = Catalog.from_dict({"streams": raw})

        # Select only administrators
        for entry in catalog.streams:
            mdata = metadata.to_map(entry.metadata)
            is_selected = entry.tap_stream_id == 'administrators'
            mdata = metadata.write(mdata, (), 'selected', is_selected)
            entry.metadata = metadata.to_list(mdata)

        result = get_selected_streams(catalog)
        self.assertEqual(result, ['administrators'])

    def test_none_selected(self):
        """When no streams are selected, returns empty list."""
        client = MagicMock()
        raw = discover_streams(client)
        catalog = Catalog.from_dict({"streams": raw})

        for entry in catalog.streams:
            mdata = metadata.to_map(entry.metadata)
            mdata = metadata.write(mdata, (), 'selected', False)
            entry.metadata = metadata.to_list(mdata)

        result = get_selected_streams(catalog)
        self.assertEqual(result, [])


class TestTopLevelFunctions(unittest.TestCase):

    @patch('tap_onfleet.json.dump')
    @patch('tap_onfleet.discover_streams')
    def test_discover_writes_catalog(self, mock_discover_streams, mock_dump):
        """discover writes a singer catalog payload to stdout."""
        mock_discover_streams.return_value = [{'stream': 'administrators'}]

        discover(MagicMock())

        mock_dump.assert_called_once_with(
            {'streams': [{'stream': 'administrators'}]},
            tap_onfleet.sys.stdout,
            indent=2,
        )

    @patch('tap_onfleet.singer.write_state')
    @patch('tap_onfleet.singer.write_schema')
    @patch('tap_onfleet.sync_stream', return_value=2)
    def test_sync_writes_schema_and_state(self, _mock_sync_stream, mock_write_schema, mock_write_state):
        """sync writes schema and state for each stream and at completion."""
        stream = MagicMock()
        stream.tap_stream_id = 'administrators'
        stream.schema.to_dict.return_value = {'properties': {'id': {'type': ['null', 'string']}}}
        stream.metadata = [
            {'breadcrumb': (), 'metadata': {'table-key-properties': ['id'], 'selected': True}},
        ]

        catalog = MagicMock()
        catalog.streams = [stream]

        class FakeStream:
            def __init__(self, client):
                self.client = client
                self.stream = None

        with patch('tap_onfleet.STREAMS', {'administrators': FakeStream}):
            sync(MagicMock(), catalog, {})

        mock_write_schema.assert_called_once_with(
            'administrators',
            {'properties': {'id': {'type': ['null', 'string']}}},
            ['id'],
        )
        self.assertEqual(mock_write_state.call_count, 2)


class TestMain(unittest.TestCase):

    @patch('tap_onfleet.discover')
    @patch('tap_onfleet.Onfleet')
    @patch('tap_onfleet.singer.utils.parse_args')
    def test_main_calls_discover_mode(self, mock_parse_args, mock_onfleet, mock_discover):
        """main executes discover branch when discover flag is set."""
        parsed = MagicMock()
        parsed.config = {
            'start_date': '2019-01-01T00:00:00Z',
            'user_agent': 'ua',
            'api_key': 'key',
            'quota_limit': 50,
        }
        parsed.discover = True
        parsed.catalog = None
        parsed.state = None
        mock_parse_args.return_value = parsed

        main.__wrapped__()

        mock_onfleet.assert_called_once()
        mock_discover.assert_called_once_with(mock_onfleet.return_value)

    @patch('tap_onfleet.sync')
    @patch('tap_onfleet.Onfleet')
    @patch('tap_onfleet.singer.utils.parse_args')
    def test_main_calls_sync_mode_with_empty_state(self, mock_parse_args, mock_onfleet, mock_sync):
        """main executes sync branch and defaults missing state to empty dict."""
        parsed = MagicMock()
        parsed.config = {
            'start_date': '2019-01-01T00:00:00Z',
            'user_agent': 'ua',
            'api_key': 'key',
            'quota_limit': 50,
        }
        parsed.discover = False
        parsed.catalog = MagicMock()
        parsed.state = None
        mock_parse_args.return_value = parsed

        main.__wrapped__()

        mock_sync.assert_called_once_with(mock_onfleet.return_value, parsed.catalog, {})
