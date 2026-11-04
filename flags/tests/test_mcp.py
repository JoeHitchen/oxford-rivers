import json
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from discharges import models as discharges
from jameson.models import Differential

from .. import models


def make_discharges():
    """An active event, a recently ended one and one too old to be reported."""

    right_now = timezone.now()
    thames = discharges.Station.objects.create(
        permit_number = 'TEST.0001',
        name = 'Thames Test',
        watercourse = 'Test Brook',
        river = discharges.Station.Rivers.THAMES,
        last_reading_at = right_now - timedelta(minutes = 10),
    )
    cherwell = discharges.Station.objects.create(
        permit_number = 'TEST.0002',
        name = 'Cherwell Test',
        watercourse = 'Cherwell Brook',
        river = discharges.Station.Rivers.CHERWELL,
        last_reading_at = right_now - timedelta(hours = 3),
    )
    active = thames.events.create(start_at = right_now - timedelta(hours = 3))
    ended = cherwell.events.create(
        start_at = right_now - timedelta(hours = 9),
        end_at = right_now - timedelta(hours = 5),
        end_seen = right_now - timedelta(hours = 4, minutes = 50),
    )
    cherwell.events.create(
        start_at = right_now - timedelta(days = 5),
        end_at = right_now - timedelta(days = 4),
        end_seen = right_now - timedelta(days = 4),
    )
    return active, ended


class Test_MCP(TestCase):
    fixtures = ['flags']

    def setUp(self):
        right_now = timezone.now() - timedelta(seconds = 1)
        for reach in models.Reach.objects.filter(has_ourcs_flag = True):
            reach.statuses.create(
                flag = models.Status.Flags.GREEN,
                set_at = right_now - timedelta(hours = 1),
                set_by = 'Test Coach',
            )
        for reach in models.Reach.objects.all():
            reach.advisories.create(
                board = models.Advisory.Boards.NONE,
                first_updated = right_now - timedelta(hours = 3),
            )

        self.differentials = [
            Differential(reach = Differential.Reach.ISIS, time = right_now, differential = 0.1267),
            Differential(
                reach = Differential.Reach.GODSTOW,
                time = right_now - timedelta(hours = 5),
                differential = 0.4568,
            ),
            Differential(reach = Differential.Reach.RADLEY, time = right_now, differential = 0.30),
        ]


    def tool_call(self, name, arguments = None):
        """Makes a real tool call to /mcp and returns the JSON-RPC result."""

        with patch(
            'flags.views.jameson.Differential.latest_by_reach',
            return_value = self.differentials,
        ):
            response = self.client.post(
                '/mcp',
                data = json.dumps({
                    'jsonrpc': '2.0',
                    'id': 1,
                    'method': 'tools/call',
                    'params': {'name': name, 'arguments': arguments or {}},
                }),
                content_type = 'application/json',
                HTTP_ACCEPT = 'application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result']['isError'])
        return response.json()['result']['structuredContent']


    def test__tools(self):
        """Lists the tool."""

        response = self.client.post(
            '/mcp',
            data = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}),
            content_type = 'application/json',
            HTTP_ACCEPT = 'application/json',
        )
        names = [tool['name'] for tool in response.json()['result']['tools']]
        self.assertIn('get_river_conditions', names)
        self.assertIn('get_recent_sewage_discharges', names)


    def test__conditions__flags(self):
        """Describes the current flag for each OURCs reach."""

        flags = self.tool_call('get_river_conditions')['flags']
        self.assertEqual(list(flags), ['isis', 'godstow'])
        for flag in flags.values():
            self.assertEqual(flag['flag'], {'code': 'G', 'label': 'Green'})
            self.assertEqual(flag['set_by'], 'Test Coach')
            self.assertFalse(flag['out_of_date'])
            self.assertRegex(flag['last_seen'], r'^\d{4}-\d\d-\d\dT[\d:.]+\+0[01]:00$')


    def test__conditions__differentials(self):
        """Describes value, staleness and band for each differential."""

        result = self.tool_call('get_river_conditions')

        self.assertEqual(list(result['differentials']), ['isis', 'godstow', 'radley'])
        self.assertEqual(result['differentials']['isis']['value'], 0.127)  # Rounded to 3 d.p.
        self.assertEqual(result['differentials']['isis']['band'], 'High Green')
        self.assertFalse(result['differentials']['isis']['out_of_date'])
        self.assertTrue(result['differentials']['godstow']['out_of_date'])
        self.assertEqual(result['differentials']['godstow']['band'], 'Green/Amber Borderline')
        self.assertIsNone(result['differentials']['radley']['band'])
    
    
    def test__conditions__advisories(self):
        """Describes the current EA board for every reach."""

        advisories = self.tool_call('get_river_conditions')['advisories']

        self.assertEqual(len(advisories), models.Reach.objects.count())
        self.assertEqual(
            list(advisories),
            [reach.tag for reach in models.Reach.objects.all()],
        )

        reach_map = {reach.tag: reach for reach in models.Reach.objects.all()}
        for reach, advisory in advisories.items():
            self.assertEqual(advisory['board'], {'code': 'NONE', 'label': 'No advisory'})
            self.assertFalse(advisory['out_of_date'])
            self.assertEqual(advisory['upstream_lock'], reach_map[reach].upstream_lock)
            self.assertEqual(advisory['downstream_lock'], reach_map[reach].downstream_lock)


    def test__conditions__transits(self):
        """Includes the transit information used by the index page."""

        transits = self.tool_call('get_river_conditions')['transits']

        self.assertEqual(
            [transit['destination'] for transit in transits],
            ['godstow', 'radley', 'abingdon'],
        )
        for transit in transits:
            self.assertEqual(transit['rowing'], 'PERMITTED')
            self.assertEqual(transit['launches'], 'PERMITTED')


    def test__conditions__no_discharges(self):
        """Reports no discharges, flagged out of date if there have been no readings."""

        result = self.tool_call('get_river_conditions')

        self.assertEqual(result['discharges']['stations_actively_discharging'], 0)
        self.assertTrue(result['discharges']['readings_out_of_date'])


    def test__conditions__recent_discharges(self):
        """Summarises the discharge stations, leaving the detail to the other tool."""

        make_discharges()

        result = self.tool_call('get_river_conditions')

        self.assertEqual(result['discharges'], {
            'stations_total': 2,
            'stations_offline': 0,
            'percentage_offline': 0.0,
            'stations_online': 2,
            'stations_actively_discharging': 1,
            'percentage_actively_discharging': 50.0,
            'stations_discharged_recently': 2,
            'percentage_discharged_recently': 100.0,
            'recent_window_hours': 48,
            'readings_out_of_date': False,
        })


    def test__conditions__times_local(self):
        """Gives every time in London time, with the offset in force at that time."""

        summer = datetime(2026, 7, 1, 12, tzinfo = dt_timezone.utc)
        winter = datetime(2026, 1, 1, 12, tzinfo = dt_timezone.utc)
        models.Status.objects.update(set_at = summer, last_seen = winter)
        models.Advisory.objects.update(first_updated = summer, last_seen = winter)
        self.differentials[0].time = summer

        result = self.tool_call('get_river_conditions')

        self.assertEqual(result['flags']['isis']['set_at'], '2026-07-01T13:00:00+01:00')
        self.assertEqual(result['flags']['isis']['last_seen'], '2026-01-01T12:00:00+00:00')
        self.assertEqual(result['differentials']['isis']['time'], '2026-07-01T13:00:00+01:00')
        self.assertEqual(result['advisories']['isis']['last_seen'], '2026-01-01T12:00:00+00:00')
        self.assertEqual(
            result['advisories']['isis']['first_updated'],
            '2026-07-01T13:00:00+01:00',
        )


    def test__discharges__no_discharges(self):
        """Returns empty lists, flagged out of date, when there is no data."""

        result = self.tool_call('get_recent_sewage_discharges')

        self.assertEqual(result['active'], [])
        self.assertEqual(result['recent'], [])
        self.assertTrue(result['summary']['readings_out_of_date'])
        self.assertEqual(result['summary']['stations_online'], 0)
        self.assertEqual(result['summary']['percentage_actively_discharging'], 0)


    def test__discharges__discharge_ordering(self):
        """Lists the most recently ended discharges first."""

        make_discharges()  # Cherwell Test ended 5 hours ago
        thames = discharges.Station.objects.get(permit_number = 'TEST.0001')
        thames.events.create(
            start_at = timezone.now() - timedelta(hours = 33),
            end_at = timezone.now() - timedelta(hours = 30),
            end_seen = timezone.now() - timedelta(hours = 30),
        )

        result = self.tool_call('get_recent_sewage_discharges')

        self.assertEqual(
            [event['station'] for event in result['recent']],
            ['Cherwell Test', 'Thames Test'],
        )


    def test__discharges__discharge_details(self):
        """Describes active and recent discharges separately, omitting those that are older."""

        active_event, ended_event = make_discharges()

        def local(moment):
            return timezone.localtime(moment).isoformat()

        expected_active = {
            'station': 'Thames Test',
            'river': 'thames',
            'watercourse': 'Test Brook',
            'start_at': local(active_event.start_at),
            'start_seen': local(active_event.start_seen),
            'end_at': None,
            'latest_update_seen': local(active_event.station.last_reading_at),
        }
        expected_recent = {
            'station': 'Cherwell Test',
            'river': 'cherwell',
            'watercourse': 'Cherwell Brook',
            'start_at': local(ended_event.start_at),
            'start_seen': local(ended_event.start_seen),
            'end_at': local(ended_event.end_at),
            'latest_update_seen': local(ended_event.end_seen),
        }

        result = self.tool_call('get_recent_sewage_discharges')

        self.assertEqual(result['summary']['stations_actively_discharging'], 1)
        self.assertEqual(
            {key: result[key] for key in ('window_hours', 'active', 'recent')},
            {'window_hours': 48, 'active': [expected_active], 'recent': [expected_recent]},
        )


    def test__discharges__consistent_with_index(self):
        """Draws on the same events as the index page."""

        make_discharges()

        with patch(
            'flags.views.jameson.Differential.latest_by_reach',
            return_value = [],
        ):
            index_events = self.client.get('/').context['discharge_events']
        result = self.tool_call('get_recent_sewage_discharges')

        self.assertEqual(
            [event.station.name for event in index_events],
            [event['station'] for event in result['active'] + result['recent']],
        )
