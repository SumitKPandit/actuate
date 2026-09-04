"""Pure parsing helpers for Story 01 ingest (no DB imports).

Shared null rule first in every parser: None, '', whitespace-only, or
case-insensitive na/null/none/nan/nat -> None.
"""

import math
from datetime import date, datetime

NULL_TOKENS = frozenset({"na", "null", "none", "nan", "nat"})

_TRIP_DATE_FMT = "%B %d, %Y"
_MOMENT_FMT = "%B %d, %Y, %I:%M %p"


def _is_nullish(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        s = value.strip()
        return s == "" or s.lower() in NULL_TOKENS
    return False


def norm_string(value: object) -> str | None:
    """Generic string column: null-rule -> None, else stripped string."""
    if _is_nullish(value):
        return None
    if isinstance(value, str):
        s = value.strip()
        return s if s else None
    return str(value).strip() or None


def norm_trip_id(value: object) -> int:
    """Strip commas -> int. Unparseable -> ValueError (join spine, fail loud)."""
    if isinstance(value, bool):
        raise ValueError(f"bad trip_id: {value!r}")  # noqa: TRY004 — spec mandates ValueError
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            raise ValueError(f"bad trip_id: {value!r}")
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() in NULL_TOKENS:
            raise ValueError(f"bad trip_id: {value!r}")
        s = s.replace(",", "")
        try:
            return int(s)
        except ValueError:
            try:
                return int(float(s))
            except ValueError:
                raise ValueError(f"bad trip_id: {value!r}") from None
    raise ValueError(f"bad trip_id: {value!r}")


def norm_stwid(value: object) -> tuple[int | None, bool]:
    """Return (value, is_placeholder). 0/'0' -> (0, True). Nullish -> (None, False)."""
    if _is_nullish(value):
        return (None, False)
    if isinstance(value, bool):
        iv = int(value)
        return (iv, iv == 0)
    if isinstance(value, int):
        return (value, value == 0)
    if isinstance(value, float):
        if math.isnan(value):
            return (None, False)
        iv = int(value)
        return (iv, iv == 0)
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if s == "" or s.lower() in NULL_TOKENS:
            return (None, False)
        try:
            iv = int(s)
        except ValueError:
            try:
                iv = int(float(s))
            except ValueError:
                return (None, False)
        return (iv, iv == 0)
    return (None, False)


def is_real_rider(stwid: int | None) -> bool:
    """Placeholder 0/None excluded from rider stats (Story 02)."""
    return stwid is not None and stwid != 0


def parse_trip_date(value: object) -> date | None:
    """'May 1, 2026' -> date. Unparseable -> None."""
    if _is_nullish(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), _TRIP_DATE_FMT).date()  # noqa: DTZ007 — dataset has no tz
    except ValueError:
        return None


def parse_iso_date(value: object) -> date | None:
    """'2026-07-09' -> date. Unparseable -> None."""
    if _is_nullish(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def parse_moment(value: object) -> datetime | None:
    """'June 3, 2026, 11:00 AM' / 'May 1, 2026, 12:03 AM' -> datetime."""
    if _is_nullish(value):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value).strip(), _MOMENT_FMT)  # noqa: DTZ007 — dataset has no tz
    except ValueError:
        return None


def parse_feedback_trip_date(value: object) -> date | None:
    """Feedback trip_date keeps the date part of the moment string."""
    dt = parse_moment(value)
    return dt.date() if dt is not None else None


def parse_feedback_creation_time(value: object) -> datetime | None:
    return parse_moment(value)


def parse_alert_time(value: object) -> datetime | None:
    return parse_moment(value)


def parse_cycle_time(value: object) -> datetime | None:
    return parse_moment(value)


def norm_float(value: object) -> float | None:
    """Null-rule -> None, else strip commas -> float. Unparseable -> None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    if isinstance(value, str):
        if _is_nullish(value):
            return None
        s = value.strip().replace(",", "")
        if s == "":
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def norm_int(value: object) -> int | None:
    """Null-rule -> None, else strip commas -> int. Unparseable -> None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value)
    if isinstance(value, str):
        if _is_nullish(value):
            return None
        s = value.strip().replace(",", "")
        if s == "":
            return None
        try:
            return int(s)
        except ValueError:
            try:
                return int(float(s))
            except ValueError:
                return None
    return None


def norm_bool(value: object) -> bool | None:
    """case-insensitive true/1 -> True, false/0 -> False; null-rule -> None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, float):
        if value == 1.0:
            return True
        if value == 0.0:
            return False
        return None
    if isinstance(value, str):
        if _is_nullish(value):
            return None
        s = value.strip().lower()
        if s in ("true", "1", "t", "yes", "y"):
            return True
        if s in ("false", "0", "f", "no", "n"):
            return False
        return None
    return None


def norm_severity(value: object) -> tuple[str | None, str | None, str | None]:
    """Return (severity, severity_raw, dq_flag) per TECH_SPEC rule 9."""
    if value is None:
        return (None, None, None)
    if isinstance(value, bool):
        if value is False:
            return (None, "False", "severity_false")
        return (None, str(value), "severity_unknown")
    if not isinstance(value, str):
        return (None, None, None)
    s = value.strip()
    if s == "" or s.lower() in NULL_TOKENS:
        return (None, None, None)
    if s.lower() == "false":
        return (None, s, "severity_false")
    if s in ("Sev-1", "Sev-2", "Sev-3"):
        return (s, s, None)
    return (None, s, "severity_unknown")


def norm_km(value: object) -> tuple[float | None, str | None]:
    """norm_float, then < 0 -> (None, 'negative_km'). Row always kept."""
    v = norm_float(value)
    if v is None:
        return (None, None)
    if v < 0:
        return (None, "negative_km")
    return (v, None)


def norm_slab(value: object) -> str | None:
    """null-rule -> None (UNSLABBED is a Story-02 display mapping)."""
    return norm_string(value)


def norm_contract(value: object) -> str | None:
    return norm_string(value)


def norm_rating(value: object) -> int | None:
    """Ratings stored raw including 0. Unparseable -> None."""
    if _is_nullish(value):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value)
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if s == "" or s.lower() in NULL_TOKENS:
            return None
        try:
            return int(s)
        except ValueError:
            try:
                return int(float(s))
            except ValueError:
                return None
    return None
