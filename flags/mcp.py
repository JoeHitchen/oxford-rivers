from typing import Any

from mcp_server import MCPToolset
from django.utils import timezone

from discharges import models as discharges

from . import views


def local_isoformat(moment):
    """ISO 8601 string in Django's local time zone, including the UTC offset."""
    return timezone.localtime(moment).isoformat()


class OxfordRiversMCP(MCPToolset):
    """Read-only river status, built from the same data and properties as the index page."""

    def get_river_conditions(self) -> dict[str, Any]:
        """Retrieve the current state of the Oxford rivers: OURCs flags, Jameson stream
        differentials (with indicative bands), EA stream advisory boards, and whether rowing and
        launch transits are permitted.

        Transit permissions of APPROVAL require a specific approval process - refer the caller to
        the OURCs rules for further details.

        Flags, differentials and advisories are each keyed by reach (e.g. `isis`, `godstow`).
        All times are Europe/London. Entries marked out_of_date have not been refreshed recently
        and should not be relied on.

        `discharges` summarises how many of Thames Water's sewage discharge stations upstream of
        Oxford are discharging, online and offline. These are only reports from the stations, so
        zero discharging is NOT evidence that the river is safe. Call get_recent_sewage_discharges
        for the details.
        """

        context = views.Index(request = self.request).get_context_data()

        return {
            'flags': {
                reach.tag: self._serialise_ourcs_flag(reach)
                for reach in context['flag_reaches']
            },
            'differentials': {
                differential.tag: self._serialise_differential(differential)
                for differential in context['differentials']
            },
            'advisories': {
                reach.tag: self._serialise_ea_advisory(reach)
                for reach in context['all_reaches']
            },
            'transits': context['transits'],
            'discharges': context['discharge_summary'],
        }


    def get_recent_sewage_discharges(self) -> dict[str, Any]:
        """Lists the sewage discharges reported by Thames Water's stations upstream of Oxford.

        `summary` provides an overall summary of the discharges and mirrors the `discharges` entry
        in get_river_conditions. `active` discharges are ongoing, and `recent` discharges ended
        within the last `window_hours`. `latest_update_seen` is when our latest information on a
        discharge is from, which can be up to `window_hours` old for an active discharge if its
        station has gone quiet.

        A lack of recent discharges should not be presented to the user as evidence that the river
        is clean. All times are Europe/London.
        """

        events = list(discharges.DischargeEvent.recent_discharges())

        return {
            'summary': discharges.Station.summary(),
            'window_hours': int(discharges.RECENT_WINDOW.total_seconds() // 3600),
            'active': [self._serialise_discharge(event) for event in events if event.is_active],
            'recent': [
                self._serialise_discharge(event) for event in events if not event.is_active
            ],
        }


    @staticmethod
    def _serialise_ourcs_flag(reach):
        return {
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
            'value': round(differential.differential, 3),  # As shown on the index page
            'unit': 'm',
            'time': local_isoformat(differential.time),
            'out_of_date': differential.out_of_date,
            'band': differential.band and differential.band.name,
        }


    @staticmethod
    def _serialise_ea_advisory(reach):
        return {
            'upstream_lock': reach.upstream_lock,
            'downstream_lock': reach.downstream_lock,
            'board': {
                'code': reach.current_advisory.board,
                'label': reach.current_advisory.get_board_display(),
            },
            'first_updated': local_isoformat(reach.current_advisory.first_updated),
            'last_updated': local_isoformat(reach.current_advisory.last_updated),
            'last_seen': local_isoformat(reach.current_advisory.last_seen),
            'out_of_date': reach.current_advisory.out_of_date,
        }


    @staticmethod
    def _serialise_discharge(event):
        return {
            'station': event.station.name,
            'river': event.station.river,
            'watercourse': event.station.watercourse,
            'start_at': local_isoformat(event.start_at),
            'start_seen': local_isoformat(event.start_seen),
            'end_at': event.end_at and local_isoformat(event.end_at),
            'latest_update_seen': (
                event.latest_update_seen
                and local_isoformat(event.latest_update_seen)
            ),
        }
