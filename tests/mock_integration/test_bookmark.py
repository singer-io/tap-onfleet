"""Mock integration test — bookmarks.

Tests that incremental streams correctly update bookmark state,
using real tap code against mocked API responses.
"""
import copy
import os
import unittest

from singer import utils

from .base import (
    OnfleetMockBaseTest, STREAM_CONFIG, INCREMENTAL_STREAMS,
    FULL_TABLE_STREAMS, SKIP_REASON,
)


@unittest.skipIf(os.getenv("USE_TAPTESTER", "").lower() == "true", SKIP_REASON)
class TestBookmark(OnfleetMockBaseTest):

    def test_incremental_streams_update_bookmarks(self):
        """Incremental streams write bookmarks after sync."""
        catalog = self._make_selected_catalog()
        state, _, _, _ = self._run_sync(catalog)

        for stream_name in INCREMENTAL_STREAMS:
            cfg = STREAM_CONFIG[stream_name]
            rep_key = cfg['replication_key']
            with self.subTest(stream=stream_name):
                bookmark = state.get('bookmarks', {}).get(stream_name, {})
                self.assertIn(rep_key, bookmark,
                              f"No bookmark for {stream_name}.{rep_key}")

    def test_full_table_streams_no_bookmark(self):
        """Full-table streams do not write bookmarks."""
        catalog = self._make_selected_catalog()
        state, _, _, _ = self._run_sync(catalog)

        for stream_name in FULL_TABLE_STREAMS:
            with self.subTest(stream=stream_name):
                bookmark = state.get('bookmarks', {}).get(stream_name, {})
                self.assertEqual(bookmark, {})

    def test_bookmark_value_matches_max_record(self):
        """Bookmark equals the max replication_key in mock records."""
        catalog = self._make_selected_catalog()
        state, _, _, _ = self._run_sync(catalog)

        for stream_name in INCREMENTAL_STREAMS:
            cfg = STREAM_CONFIG[stream_name]
            rep_key = cfg['replication_key']
            expected_max = self.get_max_bookmark(stream_name)
            with self.subTest(stream=stream_name):
                actual = state['bookmarks'][stream_name][rep_key]
                self.assertEqual(actual, expected_max)

    def test_second_sync_uses_bookmark(self):
        """A second sync picks up from the bookmark left by the first."""
        catalog = self._make_selected_catalog()

        # First sync
        state1, _, _, _ = self._run_sync(catalog)

        # Second sync starts from first sync's state
        state2, records2, _, _ = self._run_sync(catalog, state=copy.deepcopy(state1))

        # Bookmarks should still be present
        for stream_name in INCREMENTAL_STREAMS:
            cfg = STREAM_CONFIG[stream_name]
            rep_key = cfg['replication_key']
            with self.subTest(stream=stream_name):
                self.assertIn(rep_key,
                              state2.get('bookmarks', {}).get(stream_name, {}))

    def test_write_state_called(self):
        """write_state is called during sync for incremental streams."""
        catalog = self._make_selected_catalog()
        _, _, _, write_state_calls = self._run_sync(catalog)
        self.assertGreater(len(write_state_calls), 0)

    def test_bookmark_from_initial_state(self):
        """Sync with pre-set bookmarks still completes and updates state."""
        catalog = self._make_selected_catalog()

        # Set initial bookmarks before start
        initial_state = {'bookmarks': {}}
        for stream_name in INCREMENTAL_STREAMS:
            cfg = STREAM_CONFIG[stream_name]
            rep_key = cfg['replication_key']
            initial_state['bookmarks'][stream_name] = {
                rep_key: self.get_initial_bookmark_date(stream_name)
            }

        state, _, _, _ = self._run_sync(catalog, state=copy.deepcopy(initial_state))

        for stream_name in INCREMENTAL_STREAMS:
            cfg = STREAM_CONFIG[stream_name]
            rep_key = cfg['replication_key']
            with self.subTest(stream=stream_name):
                new_val = state['bookmarks'][stream_name][rep_key]
                old_val = initial_state['bookmarks'][stream_name][rep_key]
                self.assertGreaterEqual(
                    utils.strptime_with_tz(new_val),
                    utils.strptime_with_tz(old_val),
                )
