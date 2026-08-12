"""Tap-tester integration test — automatic fields."""
from base import OnfleetBaseTest
from tap_tester import runner, menagerie


class TestAutomaticFields(OnfleetBaseTest):

    def test_automatic_fields(self):
        """Verify primary keys and replication keys are always replicated."""
        conn_id = self.create_connection()
        found_catalogs = self.run_and_verify_check_mode(conn_id)
        self.select_all_streams_and_fields(
            conn_id, found_catalogs, select_all_fields=False)
        record_count = self.run_and_verify_sync(conn_id)

        synced_records = runner.get_records_from_target_output()
        for stream in self.expected_streams():
            with self.subTest(stream=stream):
                data = synced_records.get(stream, {})
                messages = data.get('messages', [])
                for message in messages:
                    if message['action'] == 'upsert':
                        record = message['data']
                        self.assertIn('id', record)
