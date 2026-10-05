"""Bound untrusted gettext input before parsing or rendering reports."""

from __future__ import annotations

from io import StringIO

MAX_CATALOG_BYTES = 8 * 1024 * 1024
MAX_CATALOG_MESSAGES = 20_000
MAX_CATALOG_LINE = 64 * 1024


class CatalogLimitError(ValueError):
    """A catalog exceeds the supported resource budget."""


def validate_catalog_size(text: str) -> None:
    """Reject oversized catalogs, physical lines and message inventories."""
    if len(text.encode("utf-8")) > MAX_CATALOG_BYTES:
        raise CatalogLimitError("Gettext catalog exceeds the 8 MiB limit")
    messages = 0
    for line in StringIO(text):
        if len(line.encode("utf-8")) > MAX_CATALOG_LINE:
            raise CatalogLimitError("Gettext catalog line exceeds the 64 KiB limit")
        if line.lstrip().startswith(("msgid ", "#~ msgid ")):
            messages += 1
            if messages > MAX_CATALOG_MESSAGES:
                raise CatalogLimitError("Gettext catalog exceeds the 20,000-message limit")
