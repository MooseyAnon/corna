"""Meta utils i.e. utils that are also used but other utils.

This is here to avoid circular dependencies while also avoiding
unnecessary code duplication.
"""

import datetime

def get_utc_now() -> datetime.datetime:
    """Get a time-zone aware datetime for "now".

    :returns: "now" as a datetime
    :rtype: datetime.datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def future(days: int = 14) -> datetime.datetime:
    """Datetime object for some number of days in the future.

    :param int days: number of days in the future
    :returns: current time + number of skip days
    :rtype: datetime.datetime
    """
    now = get_utc_now()
    skip = datetime.timedelta(days=days)
    return now + skip
