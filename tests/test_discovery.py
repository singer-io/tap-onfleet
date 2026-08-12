"""Tap-tester integration test — discovery."""
from base import OnfleetBaseTest
from tap_tester import menagerie


class TestDiscovery(OnfleetBaseTest):

    def test_discovery(self):
        """Verify discovery returns all expected streams with correct metadata."""
        conn_id = self.create_connection()
        found_catalogs = self.run_and_verify_check_mode(conn_id)

        found_catalog_names = {c['tap_stream_id'] for c in found_catalogs}
        self.assertEqual(found_catalog_names, self.expected_streams())

        for catalog in found_catalogs:
            stream = catalog['tap_stream_id']
            with self.subTest(stream=stream):
                schema = menagerie.get_annotated_schema(
                    conn_id, catalog['stream_id'])
                self.assertIn('properties', schema.get('annotated-schema', {}))
