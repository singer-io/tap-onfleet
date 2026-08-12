"""Unit tests for tap_onfleet.streams module."""
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from singer import metadata

from tap_onfleet.streams import (
    Stream, Administrators, Hubs, Organizations, Tasks, Teams, Workers,
    STREAMS,
)
from tap_onfleet.context import Context
from tap_onfleet.exceptions import OnfleetForbiddenError


class TestStreamClasses(unittest.TestCase):
    """Tests for stream class attributes and metadata."""

    def test_all_streams_registered(self):
        """STREAMS dict contains all expected stream classes."""
        expected = {'administrators', 'hubs', 'organizations',
                    'tasks', 'teams', 'workers'}
        self.assertEqual(set(STREAMS.keys()), expected)

    def test_stream_names(self):
        """Each stream class has the correct .name attribute."""
        self.assertEqual(Administrators.name, 'administrators')
        self.assertEqual(Hubs.name, 'hubs')
        self.assertEqual(Organizations.name, 'organizations')
        self.assertEqual(Tasks.name, 'tasks')
        self.assertEqual(Teams.name, 'teams')
        self.assertEqual(Workers.name, 'workers')

    def test_replication_methods(self):
        """Stream classes have the expected replication methods."""
        self.assertEqual(Administrators.replication_method, 'INCREMENTAL')
        self.assertEqual(Hubs.replication_method, 'FULL_TABLE')
        self.assertEqual(Organizations.replication_method, 'INCREMENTAL')
        self.assertEqual(Tasks.replication_method, 'INCREMENTAL')
        self.assertEqual(Teams.replication_method, 'INCREMENTAL')
        self.assertEqual(Workers.replication_method, 'INCREMENTAL')

    def test_replication_keys(self):
        """Incremental streams have a replication_key; FULL_TABLE do not."""
        self.assertEqual(Administrators.replication_key, 'timeLastModified')
        self.assertIsNone(Hubs.replication_key)
        self.assertEqual(Organizations.replication_key, 'timeLastModified')
        self.assertEqual(Tasks.replication_key, 'timeLastModified')
        self.assertEqual(Teams.replication_key, 'timeLastModified')
        self.assertEqual(Workers.replication_key, 'timeLastModified')


class TestCheckAccess(unittest.TestCase):
    """Tests for Stream.check_access()."""

    def test_logs_warning_for_forbidden_stream(self):
        """403 access failures log the expected warning message."""
        client = MagicMock()
        error_message = 'forbidden to read stream'
        client._check_endpoint.side_effect = OnfleetForbiddenError(error_message)

        stream = Administrators(client)
        with patch('tap_onfleet.streams.LOGGER.warning') as warning_mock:
            has_access = stream.check_access()

        self.assertFalse(has_access)
        warning_mock.assert_called_once_with(
            "Unauthorized Stream: %s, excluding from catalog. HTTP-Error-Message: '%s'",
            'Administrators',
            error_message,
        )


class TestLoadSchema(unittest.TestCase):
    """Tests for Stream.load_schema()."""

    def test_load_schema_returns_dict(self):
        """load_schema() returns a JSON dict with properties."""
        stream = Administrators()
        schema = stream.load_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn('properties', schema)

    def test_schema_has_id_field(self):
        """Every stream schema contains an 'id' property."""
        for name, cls in STREAMS.items():
            stream = cls()
            schema = stream.load_schema()
            with self.subTest(stream=name):
                self.assertIn('id', schema.get('properties', {}))


class TestLoadMetadata(unittest.TestCase):
    """Tests for Stream.load_metadata()."""

    def test_metadata_has_key_properties(self):
        """Metadata includes table-key-properties."""
        stream = Administrators()
        mdata = metadata.to_map(stream.load_metadata())
        key_props = metadata.get(mdata, (), 'table-key-properties')
        self.assertIn('id', key_props)

    def test_metadata_has_replication_method(self):
        """Metadata includes forced-replication-method."""
        for name, cls in STREAMS.items():
            stream = cls()
            mdata = metadata.to_map(stream.load_metadata())
            with self.subTest(stream=name):
                rep = metadata.get(mdata, (), 'forced-replication-method')
                self.assertEqual(rep, cls.replication_method)

    def test_pk_marked_automatic(self):
        """Primary key field has inclusion=automatic."""
        stream = Workers()
        mdata = metadata.to_map(stream.load_metadata())
        inclusion = metadata.get(mdata, ('properties', 'id'), 'inclusion')
        self.assertEqual(inclusion, 'automatic')

    def test_replication_key_marked_automatic(self):
        """Replication key field has inclusion=automatic."""
        stream = Tasks()
        mdata = metadata.to_map(stream.load_metadata())
        inclusion = metadata.get(
            mdata, ('properties', 'timeLastModified'), 'inclusion')
        self.assertEqual(inclusion, 'automatic')


class TestBookmarkMethods(unittest.TestCase):
    """Tests for get_bookmark, update_bookmark, is_bookmark_old."""

    def setUp(self):
        Context.config = {"start_date": "2019-01-01T00:00:00Z"}

    def test_get_bookmark_returns_start_date_when_empty(self):
        """get_bookmark() returns start_date when no bookmark in state."""
        stream = Administrators()
        state = {}
        bm = stream.get_bookmark(state)
        self.assertEqual(bm, "2019-01-01T00:00:00Z")

    def test_get_bookmark_returns_existing(self):
        """get_bookmark() returns the stored bookmark when present."""
        stream = Administrators()
        state = {'bookmarks': {'administrators': {
            'timeLastModified': '2024-03-01T00:00:00Z'
        }}}
        bm = stream.get_bookmark(state)
        self.assertEqual(bm, '2024-03-01T00:00:00Z')

    def test_update_bookmark_writes_newer(self):
        """update_bookmark writes the value if it's newer."""
        stream = Administrators()
        state = {}
        stream.update_bookmark(state, '2024-06-15T10:00:00Z')
        bm = stream.get_bookmark(state)
        self.assertEqual(bm, '2024-06-15T10:00:00Z')

    def test_update_bookmark_ignores_older(self):
        """update_bookmark does not overwrite a newer bookmark with an older one."""
        stream = Administrators()
        state = {'bookmarks': {'administrators': {
            'timeLastModified': '2024-06-15T10:00:00Z'
        }}}
        stream.update_bookmark(state, '2024-01-01T00:00:00Z')
        bm = stream.get_bookmark(state)
        self.assertEqual(bm, '2024-06-15T10:00:00Z')

    def test_is_bookmark_old_true(self):
        """is_bookmark_old returns True when value is newer than bookmark."""
        stream = Administrators()
        Context.config = {"start_date": "2019-01-01T00:00:00Z"}
        state = {}
        self.assertTrue(stream.is_bookmark_old(state, '2024-06-15T10:00:00Z'))

    def test_is_bookmark_old_false(self):
        """is_bookmark_old returns False when value is older than bookmark."""
        stream = Administrators()
        state = {'bookmarks': {'administrators': {
            'timeLastModified': '2024-06-15T10:00:00Z'
        }}}
        self.assertFalse(
            stream.is_bookmark_old(state, '2024-01-01T00:00:00Z'))


class TestSyncMethod(unittest.TestCase):
    """Tests for Stream.sync() generator."""

    def setUp(self):
        Context.config = {"start_date": "2019-01-01T00:00:00Z"}

    def test_incremental_sync_yields_tuples(self):
        """INCREMENTAL sync yields (stream, record) tuples."""
        client = MagicMock()
        client.administrators = MagicMock(return_value=[
            {'id': 'a1', 'timeLastModified': '2024-06-15 10:00:00 UTC'},
        ])
        stream = Administrators(client)
        stream.stream = MagicMock()
        state = {}
        results = list(stream.sync(state))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1]['id'], 'a1')

    def test_full_table_sync_yields_tuples(self):
        """FULL_TABLE sync yields (stream, record) tuples."""
        client = MagicMock()
        client.hubs = MagicMock(return_value=[
            {'id': 'h1', 'name': 'Hub 1'},
            {'id': 'h2', 'name': 'Hub 2'},
        ])
        stream = Hubs(client)
        stream.stream = MagicMock()
        state = {}
        results = list(stream.sync(state))
        self.assertEqual(len(results), 2)

    def test_incremental_sync_updates_bookmark(self):
        """INCREMENTAL sync updates the bookmark in state."""
        client = MagicMock()
        client.administrators = MagicMock(return_value=[
            {'id': 'a1', 'timeLastModified': '2024-03-15 10:00:00 UTC'},
            {'id': 'a2', 'timeLastModified': '2024-06-15 10:00:00 UTC'},
        ])
        stream = Administrators(client)
        stream.stream = MagicMock()
        state = {}
        list(stream.sync(state))  # consume generator
        bm = stream.get_bookmark(state)
        self.assertEqual(bm, '2024-06-15 10:00:00 UTC')
