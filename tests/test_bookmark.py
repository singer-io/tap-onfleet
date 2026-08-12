"""Tap-tester integration test — bookmarks."""
from base import OnfleetBaseTest
from tap_tester import runner, menagerie


class TestBookmark(OnfleetBaseTest):

    def test_bookmark(self):
        """Verify incremental streams update bookmarks properly."""
        conn_id = self.create_connection()
        found_catalogs = self.run_and_verify_check_mode(conn_id)
        self.select_all_streams_and_fields(conn_id, found_catalogs)

        # First sync
        self.run_and_verify_sync(conn_id)
        state1 = menagerie.get_state(conn_id)

        # Second sync
        self.run_and_verify_sync(conn_id)
        state2 = menagerie.get_state(conn_id)

        for stream, rep_keys in self.expected_replication_keys().items():
            with self.subTest(stream=stream):
                for rep_key in rep_keys:
                    bm1 = state1.get('bookmarks', {}).get(stream, {}).get(rep_key)
                    bm2 = state2.get('bookmarks', {}).get(stream, {}).get(rep_key)
                    self.assertIsNotNone(bm1)
                    self.assertIsNotNone(bm2)
                    self.assertGreaterEqual(bm2, bm1)
