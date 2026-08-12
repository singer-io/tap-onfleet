
# 
# Module dependencies.
# 

import os
import json
import singer
from tap_onfleet.streams import STREAMS
from tap_onfleet.exceptions import OnfleetForbiddenError


logger = singer.get_logger()


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def _prune_inaccessible_children(schemas: dict, field_metadata: dict) -> None:
    """
    Remove child streams from the catalog whose parent stream was excluded.
    Mutates schemas and field_metadata in place.
    """
    to_remove = []
    for name, stream_cls in list(STREAMS.items()):
        if name in schemas and getattr(stream_cls, 'parent', None) and stream_cls.parent not in schemas:
            logger.warning(
                "Stream '%s' excluded from catalog because its parent stream '%s' is not accessible.",
                name, stream_cls.parent,
            )
            schemas.pop(name, None)
            field_metadata.pop(name, None)
            to_remove.append(name)
    return to_remove


def _apply_access_checks(client, schemas: dict, field_metadata: dict) -> None:
    """
    Probe each stream for read access and remove inaccessible streams
    (and their children) from schemas and field_metadata in place.
    Raises OnfleetForbiddenError if no parent streams are accessible.
    """
    inaccessible_streams = [
        stream_name
        for stream_name, stream_obj in STREAMS.items()
        if stream_name in schemas
        and not stream_obj(client=client).check_access()
    ]

    for stream_name in inaccessible_streams:
        schemas.pop(stream_name, None)
        field_metadata.pop(stream_name, None)

    inaccessible_streams.extend(_prune_inaccessible_children(schemas, field_metadata))

    if not schemas:
        raise OnfleetForbiddenError(
            "No streams are accessible. Ensure the credentials have read permission for at least one stream."
        )
    elif inaccessible_streams:
        logger.warning(
            "Unauthorized streams excluded from catalog: %s",
            ", ".join(inaccessible_streams),
        )


def discover_streams(client):
    schemas = {}
    field_metadata = {}

    for name, stream_cls in STREAMS.items():
        instance = stream_cls(client)
        schemas[name] = singer.resolve_schema_references(instance.load_schema())
        field_metadata[name] = instance.load_metadata()

    _apply_access_checks(client, schemas, field_metadata)

    streams = []
    for name in schemas:
        streams.append({
            'stream': name,
            'tap_stream_id': name,
            'schema': schemas[name],
            'metadata': field_metadata[name],
        })
    return streams



