# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import UTC, timedelta
from zoneinfo import ZoneInfo


def local_datetime(value, timezone):
    return value.replace(tzinfo=UTC).astimezone(ZoneInfo(timezone or "UTC"))


def stay_nights(start, stop, timezone):
    if not start or not stop:
        return 0
    return (
        local_datetime(stop, timezone).date() - local_datetime(start, timezone).date()
    ).days


def add_nights(start, nights, timezone, stop=None):
    if not start:
        return False
    result = local_datetime(start, timezone) + timedelta(days=nights)
    if stop:
        previous = local_datetime(stop, timezone)
        result = result.replace(
            hour=previous.hour, minute=previous.minute, second=previous.second
        )
    return result.astimezone(UTC).replace(tzinfo=None)
