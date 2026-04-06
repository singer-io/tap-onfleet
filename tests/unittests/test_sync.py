"""Unit tests for tap_onfleet.sync module."""
import unittest
from unittest.mock import patch, MagicMock

from tap_onfleet.sync import sync_stream
from tap_onfleet.streams import Administrators, Hubs
from tap_onfleet.context import Context


class TestSyncStream(unittest.TestCase):

    def setUp(self):
        Context.config = {"start_date": "2019-01-01T00:00:00Z"}

    @patch('tap_onfleet.sync.singer.write_record')
    @patch('tap_onfleet.sync.singer.write_state')
    def test_sync_stream_incremental(self, mock_write_state, mock_write_record):
        """sync_stream writes records and state for an incremental stream."""
        client = MagicMock()
        client.administrators = MagicMock(return_value=[
            {'id': 'a1', 'timeLastModified': '2024-06-15 10:00:00 UTC',
             'name': 'Admin 1'},
        ])
        instance = Administrators(client)
        instance.stream = MagicMock()
        instance.stream.tap_stream_id = 'administrators'
        instance.stream.schema.to_dict.return_value = {
            'properties': {
                'id': {'type': ['null', 'string']},
                'timeLastModified': {'type': ['null', 'string']},
                'name': {'type': ['null', 'string']},
            }
        }
        instance.stream.metadata = [
            {'breadcrumb': (), 'metadata': {}},
        ]

        count = sync_stream({}, instance)
        self.assertEqual(count, 1)
        mock_write_record.assert_called_once()

    @patch('tap_onfleet.sync.singer.write_record')
    @patch('tap_onfleet.sync.singer.write_state')
    def test_sync_stream_full_table(self, mock_write_state, mock_write_record):
        """sync_stream writes records for a full-table stream."""
        client = MagicMock()
        client.hubs = MagicMock(return_value=[
            {'id': 'h1', 'name': 'Hub 1'},
            {'id': 'h2', 'name': 'Hub 2'},
        ])
        instance = Hubs(client)
        instance.stream = MagicMock()
        instance.stream.tap_stream_id = 'hubs'
        instance.stream.schema.to_dict.return_value = {
            'properties': {
                'id': {'type': ['null', 'string']},
                'name': {'type': ['null', 'string']},
            }
        }
        instance.stream.metadata = [
            {'breadcrumb': (), 'metadata': {}},
        ]

        count = sync_stream({}, instance)
        self.assertEqual(count, 2)
        self.assertEqual(mock_write_record.call_count, 2)
        mock_write_state.assert_not_called()  # FULL_TABLE doesn't write state
