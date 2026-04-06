"""Mock integration test — discovery.

Tests that discover_streams() returns the correct catalog metadata
for all streams, using real tap code against a mock client.
"""
import os
import unittest

from .base import OnfleetMockBaseTest, STREAM_CONFIG, ALL_STREAM_IDS, SKIP_REASON


@unittest.skipIf(os.getenv("USE_TAPTESTER", "").lower() == "true", SKIP_REASON)
class TestDiscovery(OnfleetMockBaseTest):

    def test_all_streams_discovered(self):
        """discover_streams() returns entries for every expected stream."""
        catalog = self._run_discover()
        discovered = {s.tap_stream_id for s in catalog.streams}
        self.assertEqual(discovered, ALL_STREAM_IDS)

    def test_key_properties(self):
        """Every stream declares 'id' as its table-key-properties."""
        catalog = self._run_discover()
        from singer import metadata
        for entry in catalog.streams:
            mdata = metadata.to_map(entry.metadata)
            key_props = metadata.get(mdata, (), 'table-key-properties')
            with self.subTest(stream=entry.tap_stream_id):
                self.assertIn('id', key_props)

    def test_replication_method(self):
        """Every stream has the expected forced-replication-method."""
        catalog = self._run_discover()
        from singer import metadata
        for entry in catalog.streams:
            mdata = metadata.to_map(entry.metadata)
            rep_method = metadata.get(mdata, (), 'forced-replication-method')
            expected = STREAM_CONFIG[entry.tap_stream_id]['replication_method']
            with self.subTest(stream=entry.tap_stream_id):
                self.assertEqual(rep_method, expected)

    def test_replication_key_in_metadata(self):
        """Incremental streams have valid-replication-keys in metadata."""
        catalog = self._run_discover()
        from singer import metadata
        for entry in catalog.streams:
            cfg = STREAM_CONFIG[entry.tap_stream_id]
            mdata = metadata.to_map(entry.metadata)
            valid_keys = metadata.get(mdata, (), 'valid-replication-keys')
            with self.subTest(stream=entry.tap_stream_id):
                if cfg['replication_key']:
                    self.assertIn(cfg['replication_key'], valid_keys)
                else:
                    self.assertIsNone(valid_keys)

    def test_schema_has_properties(self):
        """Every discovered stream has at least one schema property."""
        catalog = self._run_discover()
        for entry in catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                props = entry.schema.to_dict().get('properties', {})
                self.assertGreater(len(props), 0)

    def test_primary_key_in_schema(self):
        """The primary key 'id' exists in every stream's schema."""
        catalog = self._run_discover()
        for entry in catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                self.assertIn('id', entry.schema.to_dict()['properties'])

    def test_automatic_fields_marked(self):
        """PKs and replication keys have inclusion=automatic in metadata."""
        catalog = self._run_discover()
        from singer import metadata
        for entry in catalog.streams:
            cfg = STREAM_CONFIG[entry.tap_stream_id]
            mdata = metadata.to_map(entry.metadata)
            with self.subTest(stream=entry.tap_stream_id, field='id'):
                inclusion = metadata.get(mdata, ('properties', 'id'), 'inclusion')
                self.assertEqual(inclusion, 'automatic')
            if cfg['replication_key']:
                with self.subTest(stream=entry.tap_stream_id, field=cfg['replication_key']):
                    inclusion = metadata.get(
                        mdata, ('properties', cfg['replication_key']), 'inclusion')
                    self.assertEqual(inclusion, 'automatic')
