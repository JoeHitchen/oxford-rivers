"""Sunrise and sunset times, ported from SunCalc 1.8.0 so they match those shown by OURCs."""

from datetime import datetime, time, timedelta, timezone as dt_timezone
from math import acos, asin, cos, pi, sin
from zoneinfo import ZoneInfo


LATITUDE = 51.7435313
LONGITUDE = -1.2512201
LONDON = ZoneInfo('Europe/London')

RAD = pi / 180
J1970 = 2440588
J2000 = 2451545
J0 = 0.0009
OBLIQUITY = RAD * 23.4397
SUN_ALTITUDE = -0.833 * RAD  # Upper limb touching the horizon, allowing for refraction


def _to_days(moment):
    return moment.timestamp() / 86400 - 0.5 + J1970 - J2000


def _from_julian(julian):
    return datetime.fromtimestamp((julian + 0.5 - J1970) * 86400, dt_timezone.utc)


def _solar_transit(approx_transit, mean_anomaly, ecliptic_longitude):
    return (
        J2000 + approx_transit
        + 0.0053 * sin(mean_anomaly)
        - 0.0069 * sin(2 * ecliptic_longitude)
    )


def calculate_sun_times(moment):
    """The sunrise and sunset (as aware datetimes) for the solar day nearest `moment`."""

    lw = RAD * -LONGITUDE
    phi = RAD * LATITUDE
    days = _to_days(moment)

    cycle = round(days - J0 - lw / (2 * pi))
    approx_transit = J0 + lw / (2 * pi) + cycle
    mean_anomaly = RAD * (357.5291 + 0.98560028 * approx_transit)
    ecliptic_longitude = (
        mean_anomaly
        + RAD * (
            1.9148 * sin(mean_anomaly)
            + 0.02 * sin(2 * mean_anomaly)
            + 0.0003 * sin(3 * mean_anomaly)
        )
        + RAD * 102.9372
        + pi
    )
    declination = asin(sin(OBLIQUITY) * sin(ecliptic_longitude))

    hour_angle = acos(
        (sin(SUN_ALTITUDE) - sin(phi) * sin(declination)) / (cos(phi) * cos(declination)),
    )
    set_approx = J0 + (hour_angle + lw) / (2 * pi) + cycle
    transit = _solar_transit(approx_transit, mean_anomaly, ecliptic_longitude)
    sunset = _solar_transit(set_approx, mean_anomaly, ecliptic_longitude)
    sunrise = transit - (sunset - transit)

    return _from_julian(sunrise), _from_julian(sunset)


def get_sun_times(day):
    """Sun times for a date, as OURCs displays them (London time, truncated to the minute)."""

    sunrise, sunset = calculate_sun_times(datetime.combine(day, time(12), tzinfo = LONDON))
    sunrise = sunrise.astimezone(LONDON).replace(second = 0, microsecond = 0)
    sunset = sunset.astimezone(LONDON).replace(second = 0, microsecond = 0)

    return {
        'sunrise': sunrise,
        'sunset': sunset,
        'first_boating': sunrise - timedelta(hours = 1),
        'last_landing': sunset + timedelta(hours = 1),
    }
