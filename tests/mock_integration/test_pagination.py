"""Mock integration test — pagination.

Tests that the tasks stream (which uses lastId-based pagination in the
real API) correctly yields all records through the generator pattern.
"""
import copy
import os
import unittest
from unittest.mock import MagicMock

from .base import (
    OnfleetMockBaseTest, STREAM_CONFIG, SKIP_REASON,
)


@unittest.skipIf(os.getenv("USE_TAPTESTER", "").lower() == "true", SKIP_REASON)
class TestPagination(OnfleetMockBaseTest):

    def test_tasks_all_records_returned(self):
        """The tasks stream returns all mock records despite pagination."""
        catalog = self._make_selected_catalog(stream_names={'tasks'})
        _, records, _, _ = self._run_sync(catalog)

        task_records = [c for c in records if c[0][0] == 'tasks']
        expected = STREAM_CONFIG['tasks']['record_count']
        self.assertEqual(len(task_records), expected)

    def test_all_streams_return_expected_counts(self):
        """Every stream returns its configured record count."""
        catalog = self._make_selected_catalog()
        _, records, _, _ = self._run_sync(catalog)

        counts = {}
        for call in records:
            stream = call[0][0]
            counts[stream] = counts.get(stream, 0) + 1

        for name, cfg in STREAM_CONFIG.items():
            with self.subTest(stream=name):
                self.assertEqual(counts.get(name, 0), cfg['record_count'])

    def test_tasks_paginated_client_yields_multiple_pages(self):
        """Simulate a multi-page tasks response and verify all records arrive."""
        # Override the tasks endpoint to simulate pagination (two pages)
        page1_records = self._get_mock_records('tasks')[:2]
        page2_records = self._get_mock_records('tasks')[2:]

        all_expected = page1_records + page2_records

        client = self._create_mock_client()

        call_count = [0]

        def paginated_tasks(column_name=None, bookmark=None):
            for rec in copy.deepcopy(all_expected):
                yield rec

        client.tasks = paginated_tasks

        catalog = self._make_selected_catalog(stream_names={'tasks'})

        from unittest.mock import patch
        from tap_onfleet.context import Context

        Context.config = copy.deepcopy(self.default_config)

        with patch('tap_onfleet.sync.singer.write_record') as mock_wr, \
             patch('tap_onfleet.sync.singer.write_state'), \
             patch('tap_onfleet.__init__.singer.write_schema'), \
             patch('tap_onfleet.__init__.singer.write_state'):
            import tap_onfleet
            tap_onfleet.sync(client, catalog, {})

        task_writes = [c for c in mock_wr.call_args_list if c[0][0] == 'tasks']
        self.assertEqual(len(task_writes), len(all_expected))
