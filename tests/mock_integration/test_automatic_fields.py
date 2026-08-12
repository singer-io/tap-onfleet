"""Mock integration test — automatic fields.

Tests that primary-key fields appear in records even when no extra
fields are explicitly selected.
"""
import os
import unittest

from singer import metadata

from .base import (
    OnfleetMockBaseTest, STREAM_CONFIG, ALL_STREAM_IDS, SKIP_REASON,
)


@unittest.skipIf(os.getenv("USE_TAPTESTER", "").lower() == "true", SKIP_REASON)
class TestAutomaticFields(OnfleetMockBaseTest):

    @classmethod
    def setUpClass(cls):
        # Build a catalog with all streams selected but NO fields explicitly
        # selected — only automatic fields should appear.
        catalog = cls._make_selected_catalog()

        # Mark all non-automatic fields as unselected
        for entry in catalog.streams:
            cfg = STREAM_CONFIG[entry.tap_stream_id]
            mdata = metadata.to_map(entry.metadata)
            auto_fields = {'id'}
            if cfg['replication_key']:
                auto_fields.add(cfg['replication_key'])
            for field_name in entry.schema.to_dict().get('properties', {}):
                if field_name not in auto_fields:
                    mdata = metadata.write(
                        mdata, ('properties', field_name), 'selected', False)
            entry.metadata = metadata.to_list(mdata)

        cls.state, cls.write_record_calls, cls.write_schema_calls, _ = \
            cls._run_sync(catalog)

        cls.records_by_stream = {}
        for call in cls.write_record_calls:
            stream_name = call[0][0]
            record = call[0][1]
            cls.records_by_stream.setdefault(stream_name, []).append(record)

    def test_all_streams_emit_records(self):
        """All streams emit records."""
        for name in ALL_STREAM_IDS:
            with self.subTest(stream=name):
                self.assertIn(name, self.records_by_stream)

    def test_primary_key_present(self):
        """Every record contains the primary key 'id'."""
        for name, records in self.records_by_stream.items():
            for rec in records:
                with self.subTest(stream=name):
                    self.assertIn('id', rec)

    def test_replication_key_present_for_incremental(self):
        """Incremental stream records contain the replication key."""
        for name, records in self.records_by_stream.items():
            cfg = STREAM_CONFIG[name]
            rep_key = cfg['replication_key']
            if not rep_key:
                continue
            for rec in records:
                with self.subTest(stream=name):
                    self.assertIn(rep_key, rec)
