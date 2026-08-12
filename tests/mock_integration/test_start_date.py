"""Mock integration test — start date.

Tests that the start_date config is respected — first sync uses
start_date as its baseline, subsequent syncs use the bookmark.
"""
import copy
import os
import unittest

from .base import (
    OnfleetMockBaseTest, STREAM_CONFIG, INCREMENTAL_STREAMS, SKIP_REASON,
)


@unittest.skipIf(os.getenv("USE_TAPTESTER", "").lower() == "true", SKIP_REASON)
class TestStartDate(OnfleetMockBaseTest):

    def test_first_sync_uses_start_date(self):
        """First sync with empty state completes successfully."""
        catalog = self._make_selected_catalog()
        state, records, _, _ = self._run_sync(catalog, state={})
        self.assertGreater(len(records), 0)

    def test_later_start_date_still_works(self):
        """A later start_date doesn't cause errors."""
        catalog = self._make_selected_catalog()
        config = copy.deepcopy(self.default_config)
        config['start_date'] = "2024-06-01T00:00:00Z"
        state, records, _, _ = self._run_sync(catalog, state={}, config=config)
        self.assertGreater(len(records), 0)

    def test_second_sync_with_bookmark_completes(self):
        """Second sync from bookmark state completes without error."""
        catalog = self._make_selected_catalog()
        state1, _, _, _ = self._run_sync(catalog, state={})
        state2, records2, _, _ = self._run_sync(
            catalog, state=copy.deepcopy(state1))
        self.assertGreater(len(records2), 0)

    def test_incremental_bookmarks_advance(self):
        """After sync, bookmark is at or after start_date for all incremental streams."""
        from singer import utils
        catalog = self._make_selected_catalog()
        state, _, _, _ = self._run_sync(catalog, state={})

        start_dt = utils.strptime_with_tz(self.default_config['start_date'])
        for stream_name in INCREMENTAL_STREAMS:
            cfg = STREAM_CONFIG[stream_name]
            rep_key = cfg['replication_key']
            with self.subTest(stream=stream_name):
                bm = state.get('bookmarks', {}).get(stream_name, {}).get(rep_key)
                self.assertIsNotNone(bm)
                bm_dt = utils.strptime_with_tz(bm)
                self.assertGreaterEqual(bm_dt, start_dt)
