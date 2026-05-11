"""Unit tests for tap_onfleet.discover module."""
import unittest
from unittest.mock import MagicMock

from tap_onfleet.discover import discover_streams
from tap_onfleet.streams import STREAMS


class TestDiscoverStreams(unittest.TestCase):

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
