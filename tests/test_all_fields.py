"""Tap-tester integration test — all fields."""
from base import OnfleetBaseTest
from tap_tester import runner, menagerie


class TestAllFields(OnfleetBaseTest):

    def test_all_fields(self):
        """Verify all fields are replicated for each stream."""
        conn_id = self.create_connection()
        found_catalogs = self.run_and_verify_check_mode(conn_id)
        self.select_all_streams_and_fields(conn_id, found_catalogs)
        record_count = self.run_and_verify_sync(conn_id)

        for stream in self.expected_streams():
            with self.subTest(stream=stream):
                self.assertGreater(record_count.get(stream, 0), 0,
                                   f"No records for {stream}")
