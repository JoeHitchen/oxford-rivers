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

        `differentials_available` is false if no differentials could be retrieved (for example, if
        the Jameson database is unreachable). The empty `differentials` object then means the data
        is missing, not that there is nothing to report.

        Transit permissions of APPROVAL require a specific approval process - refer the caller to
        the OURCs rules for further details.

        Flags, differentials and advisories are each keyed by reach (e.g. `isis`, `godstow`).
        All times are Europe/London. Entries marked out_of_date have not been refreshed recently
        and should not be relied on.

        `discharges` counts the sewage discharges reported by Thames Water's monitors upstream of
        Oxford (on the Thames, Cherwell and Seacourt Stream): those `active` now and those that
        have ended within the last 48 hours (`recent`). These are only reports from monitors, so
        zero is NOT evidence that the river is safe. Call get_recent_sewage_discharges for the
        details.
        """

        context = views.Index(request = self.request).get_context_data()

        return {
            'flags': {
                reach.tag: self._serialise_ourcs_flag(reach)
                for reach in context['flag_reaches']
            },
            'differentials_available': bool(context['differentials']),
            'differentials': {
                differential.tag: self._serialise_differential(differential)
                for differential in context['differentials']
            },
            'advisories': {
                reach.tag: self._serialise_ea_advisory(reach)
                for reach in context['all_reaches']
            },
            'transits': context['transits'],
            'discharges': self._summarise_discharges(
                context['discharge_events'],
                context['discharges_out_of_date'],
            ),
        }


    def get_recent_sewage_discharges(self) -> dict[str, Any]:
        """Retrieve the sewage discharges reported by Thames Water's storm discharge monitors
        upstream of Oxford, on the Thames, the Cherwell and the Seacourt Stream.

        `active` discharges are ongoing, and `recent` discharges have ended within the last
        `window_hours`. Each gives the `river` (thames, cherwell or seacourt), the monitor's
        station and `watercourse`, and when the discharge started (`start_at`) and was first seen
        by us (`start_seen`). `latest_update_seen` is when our latest information on the discharge
        is from: the last time it was seen discharging for active events (so it can be out of
        date if the monitor has gone offline), or when the end was seen for recent events.

        These are only reports from monitors, which are sometimes offline or inaccurate, so empty
        lists are NOT evidence that the river is safe. `out_of_date` is true if we have not had a
        reading from Thames Water recently, in which case nothing here should be relied on.
        All times are Europe/London.
        """

        events = list(discharges.DischargeEvent.objects.recent_listing())

        return {
            'out_of_date': discharges.Station.readings_out_of_date(),
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
    def _summarise_discharges(events, out_of_date):
        return {
            'active': sum(event.is_active for event in events),
            'recent': sum(not event.is_active for event in events),
            'out_of_date': out_of_date,
            'details_tool': 'get_recent_sewage_discharges',
        }


    @staticmethod
    def _serialise_discharge(event):
        serialised = {
            'station': event.station.name,
            'river': event.station.river,
            'watercourse': event.station.watercourse,
            'start_at': local_isoformat(event.start_at),
            'start_seen': local_isoformat(event.start_seen),
        }
        if event.end_at:
            serialised['end_at'] = local_isoformat(event.end_at)
        serialised['latest_update_seen'] = (
            event.latest_update_seen and local_isoformat(event.latest_update_seen)
        )
        return serialised
