"""Unit tests for tap_onfleet.__init__ module."""
import unittest
from unittest.mock import MagicMock, patch

from singer import metadata, Catalog

from tap_onfleet import get_selected_streams, stream_is_selected
from tap_onfleet.discover import discover_streams


class TestStreamIsSelected(unittest.TestCase):

    def test_selected_true(self):
        mdata = {(): {'selected': True}}
        self.assertTrue(stream_is_selected(mdata))

    def test_selected_false(self):
        mdata = {(): {'selected': False}}
        self.assertFalse(stream_is_selected(mdata))

    def test_selected_missing(self):
        mdata = {(): {}}
        self.assertFalse(stream_is_selected(mdata))


class TestGetSelectedStreams(unittest.TestCase):

    def test_returns_selected_only(self):
        """get_selected_streams returns only streams with selected=True."""
        client = MagicMock()
        raw = discover_streams(client)
        catalog = Catalog.from_dict({"streams": raw})

        # Select only administrators
        for entry in catalog.streams:
            mdata = metadata.to_map(entry.metadata)
            is_selected = entry.tap_stream_id == 'administrators'
            mdata = metadata.write(mdata, (), 'selected', is_selected)
            entry.metadata = metadata.to_list(mdata)

        result = get_selected_streams(catalog)
        self.assertEqual(result, ['administrators'])

    def test_none_selected(self):
        """When no streams are selected, returns empty list."""
        client = MagicMock()
        raw = discover_streams(client)
        catalog = Catalog.from_dict({"streams": raw})

        for entry in catalog.streams:
            mdata = metadata.to_map(entry.metadata)
            mdata = metadata.write(mdata, (), 'selected', False)
            entry.metadata = metadata.to_list(mdata)

        result = get_selected_streams(catalog)
        self.assertEqual(result, [])
