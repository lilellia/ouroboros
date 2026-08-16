"""Read resources contained within a package."""

from ._common import (
    Anchor,
    Package,
    as_file,
    files,
)
from ._legacy import (
    Resource,
    contents,
    is_resource,
    open_binary,
    open_text,
    path,
    read_binary,
    read_text,
)
from .abc import ResourceReader

__all__ = [
    "Anchor",
    "Package",
    "Resource",
    "ResourceReader",
    "as_file",
    "contents",
    "files",
    "is_resource",
    "open_binary",
    "open_text",
    "path",
    "read_binary",
    "read_text",
]
