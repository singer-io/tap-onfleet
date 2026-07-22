"""Unit tests for discovery access-checking in tap_onfleet."""
import unittest
from unittest.mock import MagicMock, patch

from tap_onfleet.discover import (
    discover_streams,
    _apply_access_checks,
    _prune_inaccessible_children,
)
from tap_onfleet.exceptions import OnfleetForbiddenError
from tap_onfleet.streams import STREAMS, Administrators, Stream


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_schemas_and_metadata(names=None):
    names = names or list(STREAMS.keys())
    schemas = {n: {'properties': {}} for n in names}
    field_metadata = {n: [] for n in names}
    return schemas, field_metadata


def _mock_streams(access_map):
    """Return a fake STREAMS dict driven by access_map {name: bool}."""
    mock_streams = {}
    for name, accessible in access_map.items():
        instance = MagicMock()
        instance.check_access.return_value = accessible
        instance.parent = None
        cls = MagicMock(return_value=instance)
        cls.parent = None
        mock_streams[name] = cls
    return mock_streams


# ---------------------------------------------------------------------------
# _apply_access_checks
# ---------------------------------------------------------------------------

class TestApplyAccessChecks(unittest.TestCase):

    def test_all_accessible_leaves_schemas_unchanged(self):
        """No streams are removed when all return check_access=True."""
        client = MagicMock()
        schemas, field_metadata = _make_schemas_and_metadata()
        mock_streams = _mock_streams({n: True for n in schemas})

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            _apply_access_checks(client, schemas, field_metadata)

        self.assertEqual(set(schemas.keys()), set(mock_streams.keys()))

    def test_inaccessible_stream_removed(self):
        """A stream that returns check_access=False is removed."""
        client = MagicMock()
        schemas, field_metadata = _make_schemas_and_metadata(
            ['administrators', 'hubs', 'workers']
        )
        mock_streams = _mock_streams({
            'administrators': True,
            'hubs': False,
            'workers': True,
        })

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            _apply_access_checks(client, schemas, field_metadata)

        self.assertIn('administrators', schemas)
        self.assertNotIn('hubs', schemas)
        self.assertIn('workers', schemas)

    def test_inaccessible_removed_from_field_metadata_too(self):
        """field_metadata is also pruned for an inaccessible stream."""
        client = MagicMock()
        schemas, field_metadata = _make_schemas_and_metadata(['tasks', 'teams'])
        mock_streams = _mock_streams({'tasks': False, 'teams': True})

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            _apply_access_checks(client, schemas, field_metadata)

        self.assertNotIn('tasks', field_metadata)
        self.assertIn('teams', field_metadata)

    def test_no_accessible_streams_raises_forbidden_error(self):
        """Raises OnfleetForbiddenError when every stream is inaccessible."""
        client = MagicMock()
        schemas, field_metadata = _make_schemas_and_metadata(
            ['administrators', 'hubs']
        )
        mock_streams = _mock_streams({'administrators': False, 'hubs': False})

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            with self.assertRaises(OnfleetForbiddenError):
                _apply_access_checks(client, schemas, field_metadata)

    def test_check_access_called_once_per_stream(self):
        """check_access is called exactly once for each stream in schemas."""
        client = MagicMock()
        schemas, field_metadata = _make_schemas_and_metadata(
            ['administrators', 'organizations']
        )
        mock_streams = _mock_streams(
            {'administrators': True, 'organizations': True}
        )

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            _apply_access_checks(client, schemas, field_metadata)

        for name, cls in mock_streams.items():
            instance = cls.return_value
            instance.check_access.assert_called_once()


# ---------------------------------------------------------------------------
# _prune_inaccessible_children
# ---------------------------------------------------------------------------

class TestPruneInaccessibleChildren(unittest.TestCase):

    def test_child_removed_when_parent_absent(self):
        """A child stream is pruned when its parent is not in schemas."""
        schemas = {'child_stream': {}}
        field_metadata = {'child_stream': []}

        mock_child = MagicMock()
        mock_child.parent = 'parent_stream'
        mock_streams = {'child_stream': mock_child}

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            _prune_inaccessible_children(schemas, field_metadata)

        self.assertNotIn('child_stream', schemas)
        self.assertNotIn('child_stream', field_metadata)

    def test_child_kept_when_parent_present(self):
        """A child stream is kept when its parent is in schemas."""
        schemas = {'parent_stream': {}, 'child_stream': {}}
        field_metadata = {'parent_stream': [], 'child_stream': []}

        mock_parent = MagicMock()
        mock_parent.parent = None
        mock_child = MagicMock()
        mock_child.parent = 'parent_stream'
        mock_streams = {
            'parent_stream': mock_parent,
            'child_stream': mock_child,
        }

        with patch('tap_onfleet.discover.STREAMS', mock_streams):
            _prune_inaccessible_children(schemas, field_metadata)

        self.assertIn('parent_stream', schemas)
        self.assertIn('child_stream', schemas)

    def test_no_children_in_actual_streams(self):
        """All real Onfleet streams have no parent — nothing is pruned."""
        schemas, field_metadata = _make_schemas_and_metadata()
        original_keys = set(schemas.keys())

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertEqual(set(schemas.keys()), original_keys)


# ---------------------------------------------------------------------------
# discover_streams (integration of both helpers)
# ---------------------------------------------------------------------------

class TestDiscoverStreams(unittest.TestCase):

    @patch('tap_onfleet.discover._apply_access_checks')
    def test_calls_apply_access_checks(self, mock_checks):
        """discover_streams always calls _apply_access_checks."""
        client = MagicMock()
        discover_streams(client)
        mock_checks.assert_called_once()

    @patch('tap_onfleet.discover._apply_access_checks')
    def test_returns_list_of_dicts(self, _mock):
        """discover_streams returns a list of stream-entry dicts."""
        client = MagicMock()
        result = discover_streams(client)
        self.assertIsInstance(result, list)
        for entry in result:
            self.assertIn('stream', entry)
            self.assertIn('tap_stream_id', entry)
            self.assertIn('schema', entry)
            self.assertIn('metadata', entry)

    @patch('tap_onfleet.discover._apply_access_checks')
    def test_excludes_streams_removed_by_access_checks(self, mock_checks):
        """Streams popped during _apply_access_checks are absent from result."""
        client = MagicMock()

        def remove_hubs(client, schemas, field_metadata):
            schemas.pop('hubs', None)
            field_metadata.pop('hubs', None)

        mock_checks.side_effect = remove_hubs

        result = discover_streams(client)
        names = {e['stream'] for e in result}
        self.assertNotIn('hubs', names)
        self.assertIn('administrators', names)

    @patch('tap_onfleet.discover._apply_access_checks')
    def test_all_streams_present_when_all_accessible(self, _mock):
        """All streams appear when access checks remove nothing."""
        client = MagicMock()
        result = discover_streams(client)
        names = {e['stream'] for e in result}
        self.assertEqual(names, set(STREAMS.keys()))


# ---------------------------------------------------------------------------
# Stream.check_access
# ---------------------------------------------------------------------------

class TestStreamCheckAccess(unittest.TestCase):

    def test_returns_true_when_get_succeeds(self):
        """check_access returns True when client._get raises no error."""
        client = MagicMock()
        client.start_date = '2019-01-01T00:00:00Z'
        stream = Administrators(client)
        self.assertTrue(stream.check_access())

    def test_returns_false_on_forbidden_error(self):
        """check_access returns False when client.administrators raises OnfleetForbiddenError."""
        client = MagicMock()
        client.start_date = '2019-01-01T00:00:00Z'
        client.administrators.side_effect = OnfleetForbiddenError("403 Forbidden")
        stream = Administrators(client)
        self.assertFalse(stream.check_access())

    def test_child_stream_always_returns_true(self):
        """check_access always returns True for a stream with a parent."""
        client = MagicMock()
        client.start_date = '2019-01-01T00:00:00Z'
        client.administrators.side_effect = OnfleetForbiddenError("403")

        child = Stream(client)
        child.parent = 'some_parent'
        self.assertTrue(child.check_access())

    def test_stream_method_called_on_check_access(self):
        """check_access calls the client's stream method by name."""
        client = MagicMock()
        client.start_date = '2019-01-01T00:00:00Z'
        stream = Administrators(client)

        stream.check_access()

        client.administrators.assert_called_once_with(
            Administrators.replication_key, '2019-01-01T00:00:00Z'
        )
