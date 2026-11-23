"""Cadangan pytz bila library asli tidak terpasang (hanya untuk uji)."""
from datetime import timedelta, tzinfo


class _WIB(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=7)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "WIB"

    def localize(self, dt):
        return dt.replace(tzinfo=self)


def timezone(name):
    return _WIB()
