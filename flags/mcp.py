from typing import Any

from mcp_server import MCPToolset
from django.utils import timezone

from . import views


def local_isoformat(moment):
    """ISO 8601 string in Django's local time zone, including the UTC offset."""
    return timezone.localtime(moment).isoformat()


class OxfordRiversMCP(MCPToolset):
    """Read-only river status, built from the same data and properties as the index page."""

    def get_river_conditions(self) -> dict[str, Any]:
        """Retrieve the current state of the Oxford rivers: OURCs flags, Jameson stream
        differentials (with bands), EA stream advisory boards, and whether rowing and launch
        transits are permitted.

        All times are Europe/London. Entries marked out of date or stale have not been
        refreshed recently and should not be relied on.

        `differentials_available` is false if no differentials could be retrieved (for example, if
        the Jameson database is unreachable). The empty `differentials` list then means the data
        is missing, not that there is nothing to report.
        """

        context = views.Index(request = self.request).get_context_data()

        return {
            'flags': [self._serialise_ourcs_flag(reach) for reach in context['flag_reaches']],
            'differentials_available': bool(context['differentials']),
            'differentials': [
                self._serialise_differential(differential)
                for differential in context['differentials']
            ],
            'advisories': [self._serialise_advisory(reach) for reach in context['all_reaches']],
            'transits': context['transits'],
        }


    @staticmethod
    def _serialise_ourcs_flag(reach):
        return {
            'reach': reach.tag,
            'flag': {
                'code': reach.current_flag_status.flag,
                'label': reach.current_flag_status.get_flag_display(),
            },
            'set_at': local_isoformat(reach.current_flag_status.set_at),
            'set_by': reach.current_flag_status.set_by,
            'last_seen': local_isoformat(reach.current_flag_status.last_seen),
            'out_of_date': reach.current_flag_status.out_of_date,
        }


    @staticmethod
    def _serialise_differential(differential):
        return {
            'reach': differential.tag,
            'value': differential.differential,
            'unit': 'm',
            'time': local_isoformat(differential.time),
            'stale': differential.out_of_date,
            'band': differential.band and differential.band.name,
        }


    @staticmethod
    def _serialise_advisory(reach):
        return {
            'reach': reach.tag,
            'board': {
                'code': reach.current_advisory.board,
                'label': reach.current_advisory.get_board_display(),
            },
            'first_updated': local_isoformat(reach.current_advisory.first_updated),
            'last_updated': local_isoformat(reach.current_advisory.last_updated),
            'last_seen': local_isoformat(reach.current_advisory.last_seen),
            'out_of_date': reach.current_advisory.out_of_date,
        }
