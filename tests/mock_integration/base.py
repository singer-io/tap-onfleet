"""
Base test class for mock integration tests for tap-onfleet.

These tests run the real tap code against mocked API responses — no external
tap-tester dependency required.  Mock data is generated dynamically from
the JSON schema files via MockDataGenerator.
"""
import copy
import os
import unittest
from unittest.mock import MagicMock, patch

from singer import metadata, Catalog

import tap_onfleet
from tap_onfleet.discover import discover_streams
from tap_onfleet.streams import STREAMS
from tap_onfleet.context import Context

from .mock_data_generator import MockDataGenerator


# ------------------------------------------------------------------ #
#  Skip when running under tap-tester
# ------------------------------------------------------------------ #

SKIP_REASON = (
    "Skipping mock integration test — running under tap-tester. "
    "Set USE_TAPTESTER=false or unset it to run these tests."
)

# ------------------------------------------------------------------ #
#  Paths
# ------------------------------------------------------------------ #

SCHEMAS_DIR = os.path.join(
    os.path.dirname(os.path.realpath(tap_onfleet.__file__)),
    'schemas',
)

# ------------------------------------------------------------------ #
#  Stream configuration — tap-specific
# ------------------------------------------------------------------ #

STREAM_CONFIG = {
    'administrators': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'timeLastModified',
        'record_count': 2,
    },
    'hubs': {
        'replication_method': 'FULL_TABLE',
        'replication_key': None,
        'record_count': 2,
    },
    'organizations': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'timeLastModified',
        'record_count': 1,  # API returns a single object
    },
    'tasks': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'timeLastModified',
        'record_count': 3,
    },
    'teams': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'timeLastModified',
        'record_count': 2,
    },
    'workers': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'timeLastModified',
        'record_count': 2,
    },
}

ALL_STREAM_IDS = set(STREAM_CONFIG.keys())

INCREMENTAL_STREAMS = {
    name for name, cfg in STREAM_CONFIG.items()
    if cfg['replication_method'] == 'INCREMENTAL'
}

FULL_TABLE_STREAMS = {
    name for name, cfg in STREAM_CONFIG.items()
    if cfg['replication_method'] == 'FULL_TABLE'
}


class OnfleetMockBaseTest(unittest.TestCase):
    """Shared helpers and metadata expectations for mock integration tests."""

    default_start_date = "2019-01-01T00:00:00Z"

    default_config = {
        "start_date": "2019-01-01T00:00:00Z",
        "user_agent": "test-user-agent",
        "api_key": "test-api-key",
        "quota_limit": "50",
    }

    ALL_STREAM_IDS = ALL_STREAM_IDS

    # ------------------------------------------------------------------ #
    #  Dynamic mock data
    # ------------------------------------------------------------------ #

    _generator = MockDataGenerator(SCHEMAS_DIR)

    @classmethod
    def _get_mock_records(cls, stream_name):
        """Return dynamically generated mock records for a stream."""
        cfg = STREAM_CONFIG[stream_name]
        count = cfg['record_count']
        rep_key = cfg['replication_key']

        if rep_key:
            records = []
            for i in range(count):
                rec = cls._generator.generate_record(stream_name, seed=i)
                # Set deterministic, increasing timeLastModified values
                rec[rep_key] = f"2024-0{i + 1}-15 10:00:00 UTC"
                if 'timeCreated' in rec:
                    rec['timeCreated'] = f"2023-0{i + 1}-01 00:00:00 UTC"
                records.append(rec)
            return records

        return cls._generator.generate_records(stream_name, count=count)

    # ------------------------------------------------------------------ #
    #  Mock client
    # ------------------------------------------------------------------ #

    @classmethod
    def _create_mock_client(cls):
        """Create a mock Onfleet client with dynamically generated data."""
        client = MagicMock()
        client.uri = "https://onfleet.com/api/v2/"

        def _make_list_endpoint(stream_name):
            """For streams that return a plain list (admins, hubs, teams, workers)."""
            def endpoint(column_name=None, bookmark=None):
                return copy.deepcopy(cls._get_mock_records(stream_name))
            return endpoint

        def _make_org_endpoint():
            """For organizations — returns single object via generator."""
            def endpoint(column_name=None, bookmark=None):
                records = copy.deepcopy(cls._get_mock_records('organizations'))
                for rec in records:
                    yield rec
            return endpoint

        def _make_tasks_endpoint():
            """For tasks — returns via generator (paginated in real API)."""
            def endpoint(column_name=None, bookmark=None):
                for rec in copy.deepcopy(cls._get_mock_records('tasks')):
                    yield rec
            return endpoint

        client.administrators = _make_list_endpoint('administrators')
        client.hubs = _make_list_endpoint('hubs')
        client.organizations = _make_org_endpoint()
        client.teams = _make_list_endpoint('teams')
        client.workers = _make_list_endpoint('workers')
        client.tasks = _make_tasks_endpoint()

        return client

    # ------------------------------------------------------------------ #
    #  Catalog helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def _run_discover(cls):
        """Run discover_streams() and return a Catalog."""
        client = cls._create_mock_client()
        raw_streams = discover_streams(client)
        return Catalog.from_dict({"streams": raw_streams})

    @classmethod
    def _make_selected_catalog(cls, stream_names=None):
        """Build a catalog with selected=True for the given streams."""
        catalog = cls._run_discover()
        for entry in catalog.streams:
            is_selected = stream_names is None or entry.tap_stream_id in stream_names
            mdata = metadata.to_map(entry.metadata)
            mdata = metadata.write(mdata, (), 'selected', is_selected)
            entry.metadata = metadata.to_list(mdata)
        return catalog

    # ------------------------------------------------------------------ #
    #  Sync runner
    # ------------------------------------------------------------------ #

    @classmethod
    def _run_sync(cls, catalog, state=None, config=None):
        """Run the real sync() using a mock client.

        Returns (state, write_record_calls, write_schema_calls, write_state_calls).
        """
        if state is None:
            state = {}
        if config is None:
            config = copy.deepcopy(cls.default_config)

        Context.config = config

        client = cls._create_mock_client()

        with patch('tap_onfleet.sync.singer.write_record') as mock_write_record, \
             patch('tap_onfleet.sync.singer.write_state') as mock_write_state, \
             patch('tap_onfleet.__init__.singer.write_schema') as mock_write_schema, \
             patch('tap_onfleet.__init__.singer.write_state') as mock_write_state_init:

            tap_onfleet.sync(client, catalog, state)

            # Combine write_state calls from both sync.py and __init__.py
            all_write_state_calls = (
                mock_write_state.call_args_list +
                mock_write_state_init.call_args_list
            )

            return state, mock_write_record.call_args_list, \
                mock_write_schema.call_args_list, all_write_state_calls

    # ------------------------------------------------------------------ #
    #  Bookmark helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def get_max_bookmark(cls, stream_name):
        """Return the max replication_key value from mock records."""
        cfg = STREAM_CONFIG[stream_name]
        rep_key = cfg['replication_key']
        if not rep_key:
            return None
        records = cls._get_mock_records(stream_name)
        return max(rec[rep_key] for rec in records)

    @classmethod
    def get_initial_bookmark_date(cls, stream_name):
        """Return a date between start_date and the first record."""
        return "2024-01-01 00:00:00 UTC"
