from typing import Any

from mcp_server import MCPToolset

from . import views


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

        assert self.request is not None  # Needed for MyPy
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
        status = reach.current_flag_status
        return {
            'reach': reach.tag,
            'flag': status and {'code': status.flag, 'label': status.get_flag_display()},
            'set_at': status and status.set_at.astimezone().isoformat(),
            'set_by': status and status.set_by,
            'last_seen': status and status.last_seen.astimezone().isoformat(),
            'out_of_date': status and status.out_of_date,
        }


    @staticmethod
    def _serialise_differential(differential):
        return {
            'reach': differential.tag,
            'value': differential.differential,
            'unit': 'm',
            'time': differential.time.astimezone().isoformat(),
            'stale': differential.out_of_date,
            'band': differential.band and differential.band.name,
        }


    @staticmethod
    def _serialise_advisory(reach):
        advisory = reach.current_advisory
        return {
            'reach': reach.tag,
            'board': advisory and {
                'code': advisory.board,
                'label': advisory.get_board_display(),
            },
            'first_updated': advisory and advisory.first_updated.astimezone().isoformat(),
            'last_updated': advisory and advisory.last_updated.astimezone().isoformat(),
            'last_seen': advisory and advisory.last_seen.astimezone().isoformat(),
            'out_of_date': advisory and advisory.out_of_date,
        }
