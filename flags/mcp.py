import datetime
from typing import Any

from mcp_server import MCPToolset
from django.utils import timezone

from jameson import models as jameson

from . import models, suntimes, transits


def _iso(moment):
    """Local-time ISO 8601 string with offset, or None."""
    return timezone.localtime(moment).isoformat() if moment else None


class OxfordRiversMCP(MCPToolset):
    """Read-only river status, built from the same data and properties as the index page."""

    def get_river_conditions(self, date: str | None = None) -> dict[str, Any]:
        """Retrieve the current state of the Oxford rivers: OURCs flags, Jameson stream
        differentials (with bands and trends), EA stream advisory boards, whether rowing
        and launch transits are permitted, and sunrise/sunset times.

        `date` (YYYY-MM-DD, optional) selects the day for the sun times, which default to today.
        All times are Europe/London. Entries marked out of date or stale have not been
        refreshed recently and should not be relied on.
        """

        try:
            sun_day = datetime.date.fromisoformat(date) if date else timezone.localdate()
        except ValueError:
            raise ValueError(f'Invalid date "{date}" - expected YYYY-MM-DD')

        all_reaches = models.Reach.objects.prefetch_related('advisories')
        flag_reaches = (
            models.Reach.objects.filter(has_ourcs_flag = True)
            .order_by('pk')
            .prefetch_related('statuses')
        )

        return {
            'generated_at': _iso(timezone.now()),
            'flags': [self._describe_flag(reach) for reach in flag_reaches],
            'differentials': [
                self._describe_differential(differential)
                for differential in jameson.Differential.latest_by_reach()
            ],
            'advisories': [self._describe_advisory(reach) for reach in all_reaches],
            'transits': transits.generate_transit_information(flag_reaches, all_reaches),
            'sun_times': self._describe_sun_times(sun_day),
        }


    @staticmethod
    def _describe_flag(reach):
        status = reach.current_flag_status
        return {
            'reach': reach.tag,
            'flag': status and {'code': status.flag, 'label': status.get_flag_display()},
            'set_at': status and _iso(status.set_at),
            'set_by': status and status.set_by,
            'last_seen': status and _iso(status.last_seen),
            'out_of_date': status and status.out_of_date,
        }


    @staticmethod
    def _describe_differential(differential):
        band = differential.band
        return {
            'reach': differential.tag,
            'value': differential.differential,
            'unit': 'm',
            'time': _iso(differential.time),
            'stale': differential.out_of_date,
            'band': band and band.name,
            'trend': differential.trend,
        }


    @staticmethod
    def _describe_advisory(reach):
        advisory = reach.current_advisory
        return {
            'reach': reach.tag,
            'board': advisory and {
                'code': advisory.board,
                'label': advisory.get_board_display(),
            },
            'first_updated': advisory and _iso(advisory.first_updated),
            'last_updated': advisory and _iso(advisory.last_updated),
            'last_seen': advisory and _iso(advisory.last_seen),
            'out_of_date': advisory and advisory.out_of_date,
        }


    @staticmethod
    def _describe_sun_times(day):
        return {
            'date': day.isoformat(),
            **{name: _iso(moment) for name, moment in suntimes.get_sun_times(day).items()},
        }
