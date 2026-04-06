"""Tap-tester integration test — start date."""
from base import OnfleetBaseTest
from tap_tester import runner, menagerie


class TestStartDate(OnfleetBaseTest):

    start_date = "2024-01-01T00:00:00Z"

    def test_start_date(self):
        """Verify a later start_date reduces the number of records."""
        # First connection with original (early) start date
        conn_id_1 = self.create_connection(original_properties=True)
        found_catalogs_1 = self.run_and_verify_check_mode(conn_id_1)
        self.select_all_streams_and_fields(conn_id_1, found_catalogs_1)
        record_count_1 = self.run_and_verify_sync(conn_id_1)

        # Second connection with later start date
        conn_id_2 = self.create_connection(original_properties=False)
        found_catalogs_2 = self.run_and_verify_check_mode(conn_id_2)
        self.select_all_streams_and_fields(conn_id_2, found_catalogs_2)
        record_count_2 = self.run_and_verify_sync(conn_id_2)

        for stream in self.expected_streams():
            rep_method = self.expected_replication_method().get(stream)
            if rep_method == self.INCREMENTAL:
                with self.subTest(stream=stream):
                    self.assertGreaterEqual(
                        record_count_1.get(stream, 0),
                        record_count_2.get(stream, 0),
                    )
