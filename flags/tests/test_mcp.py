import json
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from jameson.models import Differential

from .. import models


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
            Differential(reach = Differential.Reach.ISIS, time = right_now, differential = 0.12),
            Differential(
                reach = Differential.Reach.GODSTOW,
                time = right_now - timedelta(hours = 5),
                differential = 0.45,
            ),
            Differential(reach = Differential.Reach.RADLEY, time = right_now, differential = 0.3),
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


    def test__tool_listed(self):
        """Lists the tool."""

        response = self.client.post(
            '/mcp',
            data = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}),
            content_type = 'application/json',
            HTTP_ACCEPT = 'application/json',
        )
        names = [tool['name'] for tool in response.json()['result']['tools']]
        self.assertIn('get_river_conditions', names)


    def test__flags(self):
        """Describes the current flag for each OURCs reach."""

        flags = self.tool_call('get_river_conditions')['flags']
        self.assertEqual(list(flags), ['isis', 'godstow'])
        for flag in flags.values():
            self.assertEqual(flag['flag'], {'code': 'G', 'label': 'Green'})
            self.assertEqual(flag['set_by'], 'Test Coach')
            self.assertFalse(flag['out_of_date'])
            self.assertRegex(flag['last_seen'], r'^\d{4}-\d\d-\d\dT[\d:.]+\+0[01]:00$')


    def test__times_local(self):
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
        advisory = result['advisories']['isis']
        self.assertEqual(advisory['first_updated'], '2026-07-01T13:00:00+01:00')
        self.assertEqual(advisory['last_seen'], '2026-01-01T12:00:00+00:00')


    def test__differentials(self):
        """Describes value, staleness and band for each differential."""

        result = self.tool_call('get_river_conditions')
        self.assertTrue(result['differentials_available'])

        by_reach = result['differentials']
        self.assertEqual(list(by_reach), ['isis', 'godstow', 'radley'])
        self.assertEqual(by_reach['isis']['value'], 0.12)
        self.assertEqual(by_reach['isis']['band'], 'High Green')
        self.assertFalse(by_reach['isis']['out_of_date'])
        self.assertTrue(by_reach['godstow']['out_of_date'])
        self.assertEqual(by_reach['godstow']['band'], 'Green/Amber Borderline')
        self.assertIsNone(by_reach['radley']['band'])
    
    
    def test__differentials_missing(self):
        """Returns the rest of the data, flagging the differentials as unavailable, if none are
        found (the index view maps an unreachable Jameson database to the same empty list)."""
        
        self.differentials = []
        result = self.tool_call('get_river_conditions')
        
        self.assertFalse(result['differentials_available'])
        self.assertEqual(result['differentials'], {})
        self.assertEqual(len(result['flags']), 2)
        self.assertEqual(len(result['advisories']), models.Reach.objects.count())
        self.assertEqual(len(result['transits']), 3)


    def test__advisories(self):
        """Describes the current EA board for every reach."""

        advisories = self.tool_call('get_river_conditions')['advisories']

        self.assertEqual(len(advisories), models.Reach.objects.count())
        self.assertEqual(
            list(advisories),
            [reach.tag for reach in models.Reach.objects.all()],
        )
        for advisory in advisories.values():
            self.assertEqual(advisory['board'], {'code': 'NONE', 'label': 'No advisory'})
            self.assertFalse(advisory['out_of_date'])


    def test__advisories__locks(self):
        """Names the locks bounding each advisory's stretch of river."""

        advisories = self.tool_call('get_river_conditions')['advisories']

        self.assertEqual(advisories['isis']['upstream_lock'], 'Osney')
        self.assertEqual(advisories['isis']['downstream_lock'], 'Iffley')
        self.assertEqual(advisories['godstow']['upstream_lock'], 'Godstow')
        self.assertEqual(advisories['godstow']['downstream_lock'], 'Osney')


    def test__differentials__rounded(self):
        """Rounds values to the three decimal places shown on the index page."""

        self.differentials[0].differential = -0.04552
        result = self.tool_call('get_river_conditions')

        self.assertEqual(result['differentials']['isis']['value'], -0.046)


    def test__transits(self):
        """Includes the transit information used by the index page."""

        transits = self.tool_call('get_river_conditions')['transits']

        self.assertEqual(
            [transit['destination'] for transit in transits],
            ['godstow', 'radley', 'abingdon'],
        )
        for transit in transits:
            self.assertEqual(transit['rowing'], 'PERMITTED')
            self.assertEqual(transit['launches'], 'PERMITTED')
