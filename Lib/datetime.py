try:
    from _datetime import *
    from _datetime import __doc__  # noqa: F401
except ImportError:
    from _pydatetime import *

__all__ = (
    "MAXYEAR",
    "MINYEAR",
    "UTC",
    "date",
    "datetime",
    "time",
    "timedelta",
    "timezone",
    "tzinfo",
)
