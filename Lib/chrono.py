from __future__ import annotations

try:
    import _datetime as _dt  # type: ignore[import-not-found]
except ImportError:
    import _pydatetime as _dt

from contextlib import suppress
from enum import IntEnum
from functools import total_ordering
import os
from pathlib import Path
import time
from typing import Any, Literal, Self, overload
import zoneinfo

__all__ = ("Duration", "Moment", "Timezone", "Weekday", "stopwatch")

MICROSECONDS_PER_MINUTE = 60_000_000
MICROSECONDS_PER_HOUR = 60 * MICROSECONDS_PER_MINUTE
MICROSECONDS_PER_DAY = 24 * MICROSECONDS_PER_HOUR


@total_ordering
class Duration:
    def __init__(
        self,
        *,
        days: float = 0,
        hours: float = 0,
        minutes: float = 0,
        seconds: float = 0,
        milliseconds: float = 0,
        microseconds: float = 0,
    ) -> None:
        """Create a new duration from the given arguments."""
        self._us = round(
            days * MICROSECONDS_PER_DAY
            + hours * MICROSECONDS_PER_HOUR
            + minutes * MICROSECONDS_PER_MINUTE
            + seconds * 1_000_000
            + milliseconds * 1_000
            + microseconds
        )

    @property
    def days(self) -> int:
        """Return the whole number of days elapsing this duration.

        >>> Duration(hours=27).days
        1
        """
        return int(self._us // MICROSECONDS_PER_DAY)

    @property
    def hours(self) -> int:
        """Return the hour component (ignoring full days) of the duration.

        >>> Duration(days=3, hours=7, minutes=12, seconds=47.3).hours
        7
        """
        return int((self._us % MICROSECONDS_PER_DAY) // MICROSECONDS_PER_HOUR)

    @property
    def minutes(self) -> int:
        """Return the minute component (ignoring full hours) of the duration.

        >>> Duration(days=3, hours=7, minutes=12, seconds=47.3).minutes
        12
        """
        return int((self._us % MICROSECONDS_PER_HOUR) // MICROSECONDS_PER_MINUTE)

    @property
    def seconds(self) -> float:
        """Return the second component (ignoring full minutes) of the duration.
        Note that this includes the fractional part of the seconds.

        >>> Duration(days=3, hours=7, minutes=12, seconds=47.3).seconds
        47.3
        """
        return (self._us % MICROSECONDS_PER_MINUTE) / 1e6

    @property
    def microseconds(self) -> int:
        """Return the microsecond component (ignoring full seconds) of the duration.

        >>> Duration(days=3, hours=7, minutes=12, seconds=47.3).microseconds
        300000
        """
        return int(self._us % 1_000_000)

    def __format__(self, format_spec: str, /) -> str:
        """Return a string representation of the duration.

        Uses the following codes:

        %d      number of days
        %h      number of hours
        %H      number of hours, zero-padded
        %m      number of minutes
        %M      number of minutes, zero-padded
        %s      number of seconds (including microseconds: SS.ffffff)
        %S      number of seconds (integer: SS)
        %f      number of microseconds (ffffff)
        """
        return (
            format_spec.replace("%d", str(self.days))
            .replace("%H", format(self.hours, "02.0f"))
            .replace("%h", str(self.hours))
            .replace("%M", format(self.minutes, "02.0f"))
            .replace("%m", str(self.minutes))
            .replace("%S", format(self.seconds, "02.0f"))
            .replace("%s", format(self.seconds, "09.6f"))
            .replace("%f", format(self.microseconds, "06d"))
        )

    def __str__(self) -> str:
        if abs(self.days) > 0:
            return format(self, "%d days, %H:%M:%S.%f")

        return format(self, "%H:%M:%S.%f")

    def total_seconds(self) -> float:
        """Return the number of seconds (total) in the duration.

        >>> Duration(days=3, hours=7, minutes=12, seconds=47.3).total_seconds()
        285167.3
        """
        return self._us / 1e6

    def __add__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented

        return type(self)(microseconds=self._us + other._us)

    def __sub__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented

        return type(self)(microseconds=self._us - other._us)

    def __mul__(self, other: float) -> Self:
        if not isinstance(other, float):
            return NotImplemented

        return type(self)(microseconds=self._us * other)

    @overload
    def __truediv__(self, other: float) -> Self: ...

    @overload
    def __truediv__(self, other: Self) -> float: ...

    def __truediv__(self, other: float | Self) -> float | Self:
        if isinstance(other, type(self)):
            return self._us / other._us

        if isinstance(other, float):
            return type(self)(microseconds=self._us / other)

        return NotImplemented

    @overload
    def __floordiv__(self, other: float) -> Self: ...

    @overload
    def __floordiv__(self, other: Self) -> float: ...

    def __floordiv__(self, other: float | Self) -> float | Self:
        if isinstance(other, type(self)):
            return self._us // other._us

        if isinstance(other, float):
            return type(self)(microseconds=self._us // other)

        return NotImplemented

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self._us == other._us

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return self._us < other._us


class Weekday(IntEnum):
    """An Enum representing the days of the week, starting with Monday (1) and ending with Sunday (7)."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    def is_weekend(self) -> bool:
        return self in [Weekday.SATURDAY, Weekday.SUNDAY]


class Timezone:
    def __init__(self, name: str, info: zoneinfo.ZoneInfo, /) -> None:
        try:
            self._name = name
            self._info = info
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"Unknown timezone: {name}")

    @classmethod
    def from_name(cls, name: str) -> Self:
        try:
            info = zoneinfo.ZoneInfo(name)
            return cls(name, info)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"Unknown timezone: {name}")

    @classmethod
    def local(cls) -> Self:
        """Try to get the local timezone.

        We "try" because for some reason this isn't just... trivially accessible.
        """

        # if we *happen* to be in a world where a downstream user has installed tzlocal, then we'll use that
        # but since it's a third-party module, we don't ship it by default
        with suppress(ModuleNotFoundError):
            import tzlocal  # type: ignore[import-not-found]

            with suppress(ValueError):
                return cls.from_name(tzlocal.getlocalzone().key)

        # check to see if the environment variable is set
        if name := os.environ.get("TZ"):
            with suppress(ValueError):
                return cls.from_name(name)

        # fallback for Linux (and maybe MacOS?)
        with suppress(OSError):
            tzpath = Path("/etc/localtime").readlink()

            match tzpath.parts:
                case [*_, "zoneinfo", region, city]:
                    with suppress(ValueError):
                        return cls.from_name(f"{region}/{city}")

                case _:
                    pass

        # try reading /etc/timezone directly
        with suppress(OSError), open("/etc/timezone", mode="r", encoding="utf-8") as f:
            name = f.read().strip()

            with suppress(ValueError):
                return cls.from_name(name)

        # :shrug:
        raise RuntimeError("Unable to determine local timezone")

    @classmethod
    def utc(cls) -> Self:
        return cls.from_name("UTC")

    @property
    def name(self) -> str:
        return self._name

    def utc_offset(self, when: Moment | None = None) -> Duration:
        """Get the UTC offset of the timezone."""
        if when is None:
            when = Moment()

        if (offset := when._proxy.utcoffset()) is None:
            raise RuntimeError("Could not determine offset")

        return Duration(microseconds=offset.total_seconds() * 1_000_000)


@total_ordering
class Moment:
    def __init__(
        self,
        *,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        second: float | None = None,
        fold: Literal[0, 1] = 0,
        tz: Timezone | str | None = None,
    ) -> None:
        """Create a new moment from the given arguments. Any values not given will default to the current time."""
        match tz:
            case None:
                try:
                    tzinfo = Timezone.local()
                except RuntimeError:
                    # we can't do much better than just default to UTC
                    tzinfo = Timezone.utc()

            case "local":
                try:
                    tzinfo = Timezone.local()
                except RuntimeError:  # noqa: TRY203
                    # here, the user expressly wanted "local", so if we can't get it, that's an error
                    raise

            case Timezone():
                tzinfo = tz

            case str():
                try:
                    tzinfo = Timezone.from_name(tz)
                except RuntimeError:
                    raise ValueError(f"Unknown timezone: {tz}")

        # We default to using components of the current time, which means that we don't need Moment.now()
        # since Moment() just... is the current time.
        r = _dt.datetime.now(tz=tzinfo._info)

        cfg = {
            "year": r.year,
            "month": r.month,
            "day": r.day,
            "hour": r.hour,
            "minute": r.minute,
            "second": r.second,
            "microsecond": r.microsecond,
            "fold": r.fold,
        }

        if year is not None:
            cfg["year"] = year

        if month is not None:
            cfg["month"] = month

        if day is not None:
            cfg["day"] = day

        if hour is not None:
            cfg["hour"] = hour

        if minute is not None:
            cfg["minute"] = minute

        if second is not None:
            cfg["second"] = int(second)
            cfg["microsecond"] = round((second - int(second)) * 1_000_000)

        if fold is not None:
            cfg["fold"] = fold

        r = _dt.datetime(**cfg, tzinfo=tzinfo._info)

        self._year = r.year
        self._month = r.month
        self._day = r.day
        self._hour = r.hour
        self._minute = r.minute
        self._second = r.second
        self._fold = r.fold
        self._tz = tzinfo
        self._proxy = r

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def day(self) -> int:
        return self._day

    @property
    def hour(self) -> int:
        return self._hour

    @property
    def minute(self) -> int:
        return self._minute

    @property
    def second(self) -> float:
        return self._second

    @property
    def tz(self) -> Timezone:
        return self._tz

    @property
    def fold(self) -> int:
        return self._fold

    @property
    def weekday_name_abbr(self) -> str:
        """Weekday as locale-aware abbreviated name: Mon (en-US), Mo (de-DE)"""
        return self._proxy.strftime("%a")

    @property
    def weekday_name(self) -> str:
        """Weekday as locale-aware full name: e.g., Monday (en-US), Montag (de-DE)"""
        return self._proxy.strftime("%A")

    @property
    def weekday(self) -> Weekday:
        """Day of the week, starting with <1: Weekday.Monday>, ..., <7: Weekday.Sunday>"""
        return Weekday(self._proxy.strftime("%u"))

    @property
    def month_name_abbr(self) -> str:
        """Month as locale-aware abbreviated name: Jan (en-US), Jan (de-DE)"""
        return self._proxy.strftime("%b")

    @property
    def month_name(self) -> str:
        """Month as locale-aware full name: e.g., January (en-US), Januar (de-DE)"""
        return self._proxy.strftime("%B")

    @property
    def day_of_year(self) -> int:
        """Return the day of the year, e.g., Feb 15 -> 46."""
        day = self._proxy.strftime("%j")
        return int(day, 10)

    @property
    def week_number(self) -> int:
        """Return the week number of the year (Monday as first day of week).

        All days in a new year preceding the first Monday are considered to be in week 0.
        """
        week = self._proxy.strftime("%W")
        return int(week, 10)

    @staticmethod
    def _convert_format_spec(format_spec: str) -> str:
        """Convert the given format_spec to one which is compatible with Python datetime.

        We
        - replace the injected %C with the ISO-8601 format
        - replace %w with %u to force Python to use ISO-8601 weekdays (1-7)
        - replace %z with %:z to force Python to show timezone offsets with separators
        """
        return (
            format_spec.replace("%C", "%Y-%m-%dT%H:%M:%S.%f %z")
            .replace("%w", "%u")
            .replace("%z", "%:z")
        )

    def __format__(self, format_spec: str) -> str:
        """Format the datetime according to the given format string.

        %Y = year with century as a zero-padded decimal number (e.g., 0008, 1997)
        %y = year without century as a zero-padded decimal number (e.g., 08, 97)
        %m = month as a decimal number (e.g., 02, 10)
        %d = day of the month as a zero-padded decimal number (e.g., 01, 17)

        %H = hour as a decimal number using a 24-hour clock (e.g., 00, 12)
        %I = hour as a decimal number using a 12-hour clock (e.g., 01, 12)
        %p = locale-equivalent of AM, PM
        %M = minute as a decimal number (e.g., 00, 59)
        %S = second as a decimal number (e.g., 00, 59)
        %f = microsecond as a decimal number, zero-padded to 6 digits (e.g., 000000, 123456)

        %z = UTC offset in the form ±HH:MM[:SS[.ffffff]] (e.g., +00:00, -05:00, +03:30:15, -07:45:13.999788)
        %Z = timezone name (e.g., UTC, EST, America/Los_Angeles)

        %a = weekday as locale abbreviated name (e.g., Mon)
        %A = weekday as locale full name (e.g., Monday)
        %w = weekday as a decimal number, where Monday is 1 and Sunday is 7  (ISO-8601 compliant)
        %W = week number of the year (Monday as the first day of the week) (00, 01, ..., 53)
        %V = ISO 8601 week number of the year (Monday as the first day, week=1 contains 04 Jan) (01, 02, ..., 53)

        %b = month as locale abbreviated name (e.g., Jan)
        %B = month as locale full name (e.g., January)

        %j = day of year as a zero-padded decimal number (001, 002, ..., 366)

        %c = locale's appropriate date-time representation (e.g., Tue Aug 16 21:30:00 1988 (en-US))
        %C = ISO-8601 compliant date-time representation (e.g., 1988-08-16T21:30:00 -04:00)

        %x = locale's appropriate date representation (e.g., 08/16/88 (en-US))
        %X = locale's appropriate time representation (e.g., 21:30:00 (en-US))

        %% = a literal '%' character

        %G = ISO 8601 year with century as a decimal number (e.g., 0008, 1997)
        %V = ISO 8601 week number of the year (Monday as the first day of the week) (01, 02, ..., 53)
        """
        format_spec = self._convert_format_spec(format_spec)
        return self._proxy.strftime(format_spec)

    def __repr__(self) -> str:
        parts = [
            f"year={self._year}",
            f"month={self._month}",
            f"day={self._day}",
            f"hour={self._hour}",
            f"minute={self._minute}",
            f"second={self._second}",
        ]
        return f"moment({', '.join(parts)})"

    def __str__(self) -> str:
        return format(self, "%C")

    @classmethod
    def _from_python_datetime(cls, dt: _dt.datetime) -> Self:
        if dt.tzinfo is None:
            dt = dt.astimezone()

        return cls(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            second=dt.second + dt.microsecond / 1e6,
            tz=dt.tzinfo.key if hasattr(dt.tzinfo, "key") else "UTC",
        )

    @classmethod
    def from_timestamp(cls, timestamp: float) -> Self:
        return cls._from_python_datetime(_dt.datetime.fromtimestamp(timestamp))

    @classmethod
    def from_string(cls, string: str, format_spec: str = "%C") -> Self:
        format_spec = cls._convert_format_spec(format_spec)
        try:
            dt = _dt.datetime.strptime(string, format_spec)
            return cls._from_python_datetime(dt)
        except ValueError:  # noqa: TRY203
            raise

    def is_weekend(self) -> bool:
        """Check if the date points to a weekend."""
        return self.weekday.is_weekend()

    def is_leap_year(self) -> bool:
        """Check if the date points to a leap year."""
        if self.year % 4 != 0:
            return False

        if self.year % 400 == 0:
            return True

        return self.year % 100 != 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self._proxy == other._proxy

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return self._proxy < other._proxy

    def __add__(self, other: Duration) -> Self:
        if not isinstance(other, Duration):
            return NotImplemented

        return type(self)._from_python_datetime(
            self._proxy + _dt.timedelta(microseconds=round(other._us))
        )

    @overload
    def __sub__(self, other: Self) -> Duration: ...

    @overload
    def __sub__(self, other: Duration) -> Self: ...

    def __sub__(self, other: Self | Duration) -> Self | Duration:
        if isinstance(other, type(self)):
            delta: _dt.timedelta = self._proxy - other._proxy
            us = delta.days * MICROSECONDS_PER_DAY + delta.seconds * 1_000_000 + delta.microseconds
            return Duration(microseconds=us)

        if isinstance(other, Duration):
            return type(self)._from_python_datetime(
                self._proxy - _dt.timedelta(microseconds=round(other._us))
            )

        return NotImplemented

    def start_of_day(self) -> Self:
        """Return a moment corresponding to the start of this day."""
        return self.replace(hour=0, minute=0, second=0)

    def end_of_day(self) -> Self:
        """Return a moment corresponding to the end of this day."""
        return self.replace(hour=23, minute=59, second=59.999999)

    def _as_dict(self) -> dict[str, float]:
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
        }

    def replace(self, **kwargs) -> Self:
        """Return a copy of this moment with the specified fields replaced."""
        cfg = {**self._as_dict(), **kwargs}
        return type(self)(**cfg)

    def as_timezone(self, tz: Timezone | str | None) -> Self:
        """Return a copy of this moment in the specified timezone."""
        match tz:
            case None | "local":
                tz = Timezone.local()

            case Timezone():
                pass

            case str():
                tz = Timezone.from_name(tz)

        return type(self)._from_python_datetime(self._proxy.astimezone(tz._info))

    def humanize(self) -> str:
        """Return a humanized string representation of this moment."""
        now = type(self)()

        if self < now:
            delta = now - self

            if delta.days > 1:
                return f"{delta.days} days ago"

            if delta.days == 1:
                return "yesterday"

            if delta.hours > 1:
                return f"{delta.hours} hours ago"

            if delta.hours == 1:
                return "an hour ago"

            if delta.minutes > 1:
                return f"{delta.minutes} minutes ago"

            if delta.minutes == 1:
                return "a minute ago"

            if delta.seconds > 1:
                return f"{delta.seconds} seconds ago"

            return "just now"

        elif self > now:
            delta = self - now

            if delta.days > 1:
                return f"in {delta.days} days"

            if delta.days == 1:
                return "tomorrow"

            if delta.hours > 1:
                return f"in {delta.hours} hours"

            if delta.hours == 1:
                return "in an hour"

            if delta.minutes > 1:
                return f"in {delta.minutes} minutes"

            if delta.minutes == 1:
                return "in a minute"

            if delta.seconds > 1:
                return f"in {delta.seconds} seconds"

            return "in a moment"

        return "now"


class stopwatch:
    def __init__(self) -> None:
        self._start: int | None = None
        self._end: int | None = None

    @property
    def duration(self) -> Duration:
        if self._start is None:
            # we haven't started, so the stopwatch reads 0
            return Duration()

        # if we've already ended, look back at the end time
        # if we haven't, then the stopwatch is currently running and we'll use the current time
        end = self._end if self._end is not None else time.perf_counter_ns()

        ns = end - self._start
        return Duration(microseconds=round(ns / 1000))

    def start(self) -> None:
        self._start = time.perf_counter_ns()
        self._end = None

    def stop(self) -> None:
        if self._start is None:
            # the stopwatch isn't running, so we just don't do anything
            # except make sure that _end is None (which it should be)
            self._end = None
            return

        self._end = time.perf_counter_ns()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()


def sleep(t: int | Duration) -> None:
    """Sleep for the given length of time. If the argument is an int, sleep that many milliseconds."""
    match t:
        case int():
            time.sleep(t / 1000)

        case Duration():
            time.sleep(t.total_seconds())
