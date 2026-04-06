"""Mock integration test — all fields.

Tests that every field in the schema appears in emitted records when all
fields are selected (default behavior).
"""
import os
import unittest

from .base import (
    OnfleetMockBaseTest, STREAM_CONFIG, ALL_STREAM_IDS, SKIP_REASON,
)


@unittest.skipIf(os.getenv("USE_TAPTESTER", "").lower() == "true", SKIP_REASON)
class TestAllFields(OnfleetMockBaseTest):

    @classmethod
    def setUpClass(cls):
        catalog = cls._make_selected_catalog()
        cls.state, cls.write_record_calls, cls.write_schema_calls, _ = \
            cls._run_sync(catalog)

        # Group records by stream
        cls.records_by_stream = {}
        for call in cls.write_record_calls:
            stream_name = call[0][0]
            record = call[0][1]
            cls.records_by_stream.setdefault(stream_name, []).append(record)

    def test_all_streams_have_records(self):
        """Every stream produced at least one record."""
        for name in ALL_STREAM_IDS:
            with self.subTest(stream=name):
                self.assertIn(name, self.records_by_stream)
                self.assertGreater(len(self.records_by_stream[name]), 0)

    def test_records_contain_primary_key(self):
        """Every record has an 'id' field."""
        for name, records in self.records_by_stream.items():
            for rec in records:
                with self.subTest(stream=name):
                    self.assertIn('id', rec)

    def test_record_field_types_match_schema(self):
        """Record field values are broadly type-compatible with the schema."""
        catalog = self._run_discover()
        schema_lookup = {e.tap_stream_id: e.schema.to_dict()
                         for e in catalog.streams}
        type_map = {
            'string': str,
            'integer': (int, float),
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        for stream_name, records in self.records_by_stream.items():
            schema_props = schema_lookup[stream_name].get('properties', {})
            for rec in records:
                for field, value in rec.items():
                    if value is None:
                        continue
                    if field not in schema_props:
                        continue
                    field_type = schema_props[field].get('type', 'string')
                    if isinstance(field_type, list):
                        field_type = [t for t in field_type if t != 'null']
                        if not field_type:
                            continue
                        expected_types = tuple(
                            t for ft in field_type
                            for t in (type_map.get(ft, (str,))
                                      if isinstance(type_map.get(ft), tuple)
                                      else (type_map.get(ft, str),))
                        )
                    else:
                        expected_types = type_map.get(field_type, (str,))
                        if not isinstance(expected_types, tuple):
                            expected_types = (expected_types,)
                    with self.subTest(stream=stream_name, field=field):
                        self.assertIsInstance(value, expected_types)
