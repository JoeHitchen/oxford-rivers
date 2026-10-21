import json
from datetime import timedelta
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
            'flags.mcp.jameson.Differential.latest_by_reach',
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
        return response.json()['result']


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

        result = self.tool_call('get_river_conditions')
        self.assertFalse(result['isError'])

        flags = result['structuredContent']['flags']
        self.assertEqual([flag['reach'] for flag in flags], ['isis', 'godstow'])
        for flag in flags:
            self.assertEqual(flag['flag'], {'code': 'G', 'label': 'Green'})
            self.assertEqual(flag['set_by'], 'Test Coach')
            self.assertFalse(flag['out_of_date'])
            self.assertRegex(flag['last_seen'], r'^\d{4}-\d\d-\d\dT[\d:.]+\+0[01]:00$')


    def test__flag_missing(self):
        """Reports null rather than failing for a reach that has never had a flag."""

        models.Status.objects.filter(reach__tag = 'godstow').delete()

        flags = self.tool_call('get_river_conditions')['structuredContent']['flags']
        self.assertIsNone(flags[1]['flag'])


    def test__differentials(self):
        """Describes value, staleness and band for each differential."""

        result = self.tool_call('get_river_conditions')
        by_reach = {d['reach']: d for d in result['structuredContent']['differentials']}

        self.assertEqual(list(by_reach), ['isis', 'godstow', 'radley'])
        self.assertEqual(by_reach['isis']['value'], 0.12)
        self.assertEqual(by_reach['isis']['band'], 'High Green')
        self.assertFalse(by_reach['isis']['stale'])
        self.assertTrue(by_reach['godstow']['stale'])
        self.assertEqual(by_reach['godstow']['band'], 'Green/Amber Borderline')
        self.assertIsNone(by_reach['radley']['band'])


    def test__advisories(self):
        """Describes the current EA board for every reach."""

        result = self.tool_call('get_river_conditions')
        advisories = result['structuredContent']['advisories']

        self.assertEqual(len(advisories), models.Reach.objects.count())
        for advisory in advisories:
            self.assertEqual(advisory['board'], {'code': 'NONE', 'label': 'No advisory'})
            self.assertFalse(advisory['out_of_date'])


    def test__transits(self):
        """Includes the transit information used by the index page."""

        result = self.tool_call('get_river_conditions')
        transits = result['structuredContent']['transits']

        self.assertEqual(
            [transit['destination'] for transit in transits],
            ['godstow', 'radley', 'abingdon'],
        )
        for transit in transits:
            self.assertEqual(transit['rowing'], 'PERMITTED')
            self.assertEqual(transit['launches'], 'PERMITTED')
