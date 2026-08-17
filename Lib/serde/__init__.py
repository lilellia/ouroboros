from types import SimpleNamespace
from typing import Any, Literal

from serde import (
    json as _json,
    tomllib as _toml,
)

__all__ = ["json", "toml"]

# Because we're wrapping the original Python json and tomllib modules (which are submodules here in serde/*),
# it'd be a bit messy to stick these serde.{json,toml,yaml} namespaces as serde/json.py, etc.
#
# And since they're simple two-function pairs, SimpleNamespace seems like a fair compromise.

################################################################################
### JSON
################################################################################


def _json_encode(obj: Any, /) -> str:
    """Return a JSON string representation of the given object.

    >>> data = dict(a=2, b=[1, 2, 3], c={"d": "e"})
    >>> datafmt.json.encode(data)
    '{"a": 2, "b": [1, 2, 3], "c": {"d": "e"}}'
    """
    return _json.dumps(obj)


def _json_decode(s: str, /) -> Any:
    """Parse the given JSON string representation.

    >>> s = '{"a": 2, "b": [1, 2, 3], "c": {"d": "e"}}'
    >>> datafmt.json.decode(s)
    {'a': 2, 'b': [1, 2, 3], 'c': {'d': 'e'}}
    """
    return _json.loads(s)


json = SimpleNamespace(encode=_json_encode, decode=_json_decode)


################################################################################
### TOML
################################################################################


def _toml_encode(obj: Any, /) -> str:
    """Return a JSON string representation of the given object."""
    # TODO: get a TOML writer (and yell at tomllib in the meantime)
    raise NotImplementedError


def _toml_decode(s: str, /) -> Any:
    """Parse the given TOML string representation.

    >>> s = 'a = 2\nb = [1, 2, 3]\n[c]\nd = "e"'
    >>> datafmt.toml.decode(s)
    {'a': 2, 'b': [1, 2, 3], 'c': {'d': 'e'}}
    """
    return _toml.loads(s)


toml = SimpleNamespace(encode=_toml_encode, decode=_toml_decode)

################################################################################
### top-level functions
################################################################################


def decode(s: str, /, fmt: Literal["json", "toml"]) -> Any:
    match fmt:
        case "json":
            return json.decode(s)

        case "toml":
            return toml.decode(s)

        case _:
            raise ValueError(f"invalid format: {fmt!r}")


def encode(obj: Any, /, fmt: Literal["json", "toml"]) -> str:
    match fmt:
        case "json":
            return json.encode(obj)

        case "toml":
            return toml.encode(obj)

        case _:
            raise ValueError(f"invalid format: {fmt!r}")
