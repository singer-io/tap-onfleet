"""
Base test class for tap-tester integration tests for tap-onfleet.

These tests require a real Onfleet API account and are designed to run
under the tap-tester framework with real credentials.
"""
import os
import unittest

from tap_tester import connections, menagerie, runner


class OnfleetBaseTest(unittest.TestCase):
    """Setup expectations for tap-tester sub-classes."""

    start_date = "2019-01-01T00:00:00Z"

    FULL_TABLE = "FULL_TABLE"
    INCREMENTAL = "INCREMENTAL"
    PRIMARY_KEYS = "primary_keys"

    @staticmethod
    def tap_name():
        return "tap-onfleet"

    @staticmethod
    def get_type():
        return "platform.onfleet"

    def get_properties(self, original=True):
        return_value = {
            'start_date': '2019-01-01T00:00:00Z',
            'user_agent': 'Stitch (+support@stitchdata.com)',
            'quota_limit': '50',
        }
        if original:
            return return_value

        return_value["start_date"] = self.start_date
        return return_value

    def get_credentials(self):
        return {
            'api_key': os.getenv('TAP_ONFLEET_API_KEY'),
        }

    @classmethod
    def expected_metadata(cls):
        return {
            "administrators": {
                cls.PRIMARY_KEYS: {"id"},
                "replication_method": cls.INCREMENTAL,
                "replication_key": "timeLastModified",
            },
            "hubs": {
                cls.PRIMARY_KEYS: {"id"},
                "replication_method": cls.FULL_TABLE,
                "replication_key": None,
            },
            "organizations": {
                cls.PRIMARY_KEYS: {"id"},
                "replication_method": cls.INCREMENTAL,
                "replication_key": "timeLastModified",
            },
            "tasks": {
                cls.PRIMARY_KEYS: {"id"},
                "replication_method": cls.INCREMENTAL,
                "replication_key": "timeLastModified",
            },
            "teams": {
                cls.PRIMARY_KEYS: {"id"},
                "replication_method": cls.INCREMENTAL,
                "replication_key": "timeLastModified",
            },
            "workers": {
                cls.PRIMARY_KEYS: {"id"},
                "replication_method": cls.INCREMENTAL,
                "replication_key": "timeLastModified",
            },
        }

    def expected_streams(self):
        return set(self.expected_metadata().keys())

    def expected_primary_keys(self):
        return {
            name: meta[self.PRIMARY_KEYS]
            for name, meta in self.expected_metadata().items()
        }

    def expected_replication_method(self):
        return {
            name: meta['replication_method']
            for name, meta in self.expected_metadata().items()
        }

    def expected_replication_keys(self):
        return {
            name: {meta['replication_key']}
            for name, meta in self.expected_metadata().items()
            if meta['replication_key']
        }

    def setUp(self):
        missing_envs = [
            x for x in ['TAP_ONFLEET_API_KEY']
            if os.environ.get(x) is None
        ]
        if missing_envs:
            raise unittest.SkipTest(
                "Missing environment variables: {}".format(missing_envs))

    def create_connection(self, original_properties=True):
        conn_id = connections.ensure_connection(
            self, original_properties=original_properties)
        return conn_id

    def run_and_verify_check_mode(self, conn_id):
        check_job_name = runner.run_check_mode(self, conn_id)
        exit_status = menagerie.get_exit_status(conn_id, check_job_name)
        menagerie.verify_check_exit_status(self, exit_status, check_job_name)
        found_catalogs = menagerie.get_catalogs(conn_id)
        self.assertGreater(len(found_catalogs), 0)
        return found_catalogs

    def select_all_streams_and_fields(self, conn_id, catalogs,
                                       select_all_fields=True):
        for catalog in catalogs:
            schema = menagerie.get_annotated_schema(
                conn_id, catalog['stream_id'])

            non_selected_properties = []
            if not select_all_fields:
                non_selected_properties = set(
                    schema.get('annotated-schema', {}).get(
                        'properties', {}).keys()
                )

            connections.select_catalog_and_fields_via_metadata(
                conn_id, catalog, schema, non_selected_properties)

    def run_and_verify_sync(self, conn_id):
        sync_job_name = runner.run_sync_mode(self, conn_id)
        exit_status = menagerie.get_exit_status(conn_id, sync_job_name)
        menagerie.verify_sync_exit_status(self, exit_status, sync_job_name)
        sync_record_count = runner.examine_target_output_file(
            self, conn_id,
            self.expected_streams(),
            self.expected_primary_keys())
        return sync_record_count
