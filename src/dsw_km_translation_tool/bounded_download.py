"""Read HTTP bodies with finite memory and elapsed-time budgets."""

from __future__ import annotations

import time
from collections.abc import Callable

from .catalog_limits import MAX_CATALOG_BYTES, CatalogLimitError

DOWNLOAD_SECONDS = 60.0
IO_TIMEOUT_SECONDS = 10.0


def read_bounded_response(
    response,
    *,
    deadline: float,
    max_bytes: int = MAX_CATALOG_BYTES,
    clock: Callable[[], float] = time.monotonic,
) -> bytes:
    """Check the deadline between single buffered reads; never read an entire body."""
    length = response.headers.get("Content-Length")
    if length is not None:
        try:
            declared_length = int(length)
        except ValueError as error:
            raise CatalogLimitError("HTTP response has an invalid Content-Length") from error
        if declared_length < 0 or declared_length > max_bytes:
            raise CatalogLimitError("HTTP response exceeds the download byte limit")
    data = bytearray()
    while True:
        if clock() >= deadline:
            raise CatalogLimitError("HTTP download exceeded its elapsed-time budget")
        chunk = response.read1(min(64 * 1024, max_bytes + 1 - len(data)))
        if clock() >= deadline:
            raise CatalogLimitError("HTTP download exceeded its elapsed-time budget")
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        if len(data) > max_bytes:
            raise CatalogLimitError("HTTP response exceeds the download byte limit")
