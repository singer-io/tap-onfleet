
# 
# Module dependencies.
# 

import os
import json
import singer
from tap_onfleet.streams import STREAMS
from tap_onfleet.exceptions import OnfleetForbiddenError


LOGGER = singer.get_logger()


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def _prune_inaccessible_children(accessible: set) -> set:
    """
    Remove child streams whose parent stream was excluded.
    Returns the pruned set of accessible stream names.
    """
    pruned = set(accessible)
    for name, stream_cls in STREAMS.items():
        if name in pruned and stream_cls.parent and stream_cls.parent not in pruned:
            LOGGER.warning(
                "Stream '%s' excluded from catalog because its parent stream '%s' is not accessible.",
                name,
                stream_cls.parent,
            )
            pruned.discard(name)
    return pruned


def _apply_access_checks(client, stream_names: list) -> list:
    """
    Probe each stream for read access and return the list of accessible stream names.
    Raises OnfleetForbiddenError if no streams are accessible.
    """
    inaccessible = [
        name
        for name in stream_names
        if not STREAMS[name](client=client).check_access()
    ]

    accessible = set(stream_names) - set(inaccessible)
    accessible = _prune_inaccessible_children(accessible)

    if not accessible:
        raise OnfleetForbiddenError(
            "HTTP-error-code: 403, Error: The credentials do not have 'read' access to any supported streams."
        )

    if inaccessible:
        LOGGER.warning(
            "No 'read' access to stream(s): %s. Excluded from catalog.",
            ", ".join(inaccessible),
        )

    return list(accessible)


def discover_streams(client):
    all_stream_names = list(STREAMS.keys())
    accessible_names = _apply_access_checks(client, all_stream_names)

    streams = []
    for name in all_stream_names:
        if name not in accessible_names:
            continue
        s = STREAMS[name](client)
        schema = singer.resolve_schema_references(s.load_schema())
        streams.append({'stream': s.name, 'tap_stream_id': s.name, 'schema': schema, 'metadata': s.load_metadata()})
    return streams



