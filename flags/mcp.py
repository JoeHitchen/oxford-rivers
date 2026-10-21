from typing import Any

from mcp_server import MCPToolset
from django.utils import timezone

from . import views


def _iso(moment):
    """Local-time ISO 8601 string with offset, or None."""
    return timezone.localtime(moment).isoformat() if moment else None


class OxfordRiversMCP(MCPToolset):
    """Read-only river status, built from the same data and properties as the index page."""

    def get_river_conditions(self) -> dict[str, Any]:
        """Retrieve the current state of the Oxford rivers: OURCs flags, Jameson stream
        differentials (with bands), EA stream advisory boards, and whether rowing and launch
        transits are permitted.

        All times are Europe/London. Entries marked out of date or stale have not been
        refreshed recently and should not be relied on.
        """

        assert self.request is not None  # Needed for MyPy
        context = views.Index(request = self.request).get_context_data()

        # The index page tolerates an unreachable Jameson database, but the differentials
        # should always be populated so an empty list is treated as a failure here
        if not context['differentials']:
            raise RuntimeError('No differentials available - the Jameson database may be down')

        return {
            'generated_at': _iso(timezone.now()),
            'flags': [self._describe_flag(reach) for reach in context['flag_reaches']],
            'differentials': [
                self._describe_differential(differential)
                for differential in context['differentials']
            ],
            'advisories': [self._describe_advisory(reach) for reach in context['all_reaches']],
            'transits': context['transits'],
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
