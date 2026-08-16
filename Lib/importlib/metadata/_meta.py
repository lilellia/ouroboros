from collections.abc import Iterator
from typing import (
    Any,
    Protocol,
    TypeVar,
    overload,
)

_T = TypeVar("_T")


class PackageMetadata(Protocol):
    def __len__(self) -> int: ...  # pragma: no cover

    def __contains__(self, item: str) -> bool: ...  # pragma: no cover

    def __getitem__(self, key: str) -> str: ...  # pragma: no cover

    def __iter__(self) -> Iterator[str]: ...  # pragma: no cover

    @overload
    def get(self, name: str, failobj: None = None) -> str | None: ...  # pragma: no cover

    @overload
    def get(self, name: str, failobj: _T) -> str | _T: ...  # pragma: no cover

    # overload per python/importlib_metadata#435
    @overload
    def get_all(self, name: str, failobj: None = None) -> list[Any] | None: ...  # pragma: no cover

    @overload
    def get_all(self, name: str, failobj: _T) -> list[Any] | _T:
        """
        Return all values associated with a possibly multi-valued key.
        """

    @property
    def json(self) -> dict[str, str | list[str]]:
        """
        A JSON-compatible form of the metadata.
        """


class SimplePath(Protocol[_T]):
    """
    A minimal subset of pathlib.Path required by PathDistribution.
    """

    def joinpath(self) -> _T: ...  # pragma: no cover

    def __truediv__(self, other: str | _T) -> _T: ...  # pragma: no cover

    @property
    def parent(self) -> _T: ...  # pragma: no cover

    def read_text(self) -> str: ...  # pragma: no cover
