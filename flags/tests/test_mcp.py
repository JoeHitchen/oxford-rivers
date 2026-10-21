import json
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import PropertyMock, patch

from django.test import TestCase, SimpleTestCase
from django.utils import timezone

from jameson.models import Differential

from .. import models, suntimes


class Test_SunTimes(SimpleTestCase):

    # Reference values are from SunCalc 1.8.0 (as used by OURCs) at 51.7435313, -1.2512201,
    # displayed in London time, either side of both 2026 clock changes
    REFERENCE = {
        date(2026, 3, 28): ('05:51', '18:31'),
        date(2026, 3, 29): ('06:48', '19:33'),  # Clocks go forward
        date(2026, 3, 30): ('06:46', '19:34'),
        date(2026, 6, 21): ('04:47', '21:28'),
        date(2026, 10, 24): ('07:45', '17:55'),
        date(2026, 10, 25): ('06:47', '16:53'),  # Clocks go back
        date(2026, 10, 26): ('06:49', '16:51'),
        date(2026, 12, 21): ('08:10', '15:57'),
    }

    def test__matches_suncalc(self):
        """Sunrise and sunset match those OURCs displays, including across clock changes."""

        for day, (sunrise, sunset) in self.REFERENCE.items():
            with self.subTest(day):
                times = suntimes.get_sun_times(day)
                self.assertEqual(times['sunrise'].strftime('%H:%M'), sunrise)
                self.assertEqual(times['sunset'].strftime('%H:%M'), sunset)


    def test__boating_window(self):
        """First boating is an hour before sunrise and last landing an hour after sunset."""

        for day in self.REFERENCE:
            with self.subTest(day):
                times = suntimes.get_sun_times(day)
                self.assertEqual(times['sunrise'] - times['first_boating'], timedelta(hours = 1))
                self.assertEqual(times['last_landing'] - times['sunset'], timedelta(hours = 1))


    def test__london_offsets(self):
        """Times carry the offset in force on the day."""

        self.assertEqual(
            suntimes.get_sun_times(date(2026, 3, 28))['sunrise'].utcoffset(),
            timedelta(0),
        )
        self.assertEqual(
            suntimes.get_sun_times(date(2026, 3, 29))['sunrise'].utcoffset(),
            timedelta(hours = 1),
        )


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

        with (
            patch(
                'flags.mcp.jameson.Differential.latest_by_reach',
                return_value = self.differentials,
            ),
            patch.object(Differential, 'trend', new_callable = PropertyMock) as trend,
        ):
            trend.return_value = 'rising'
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
        """Describes value, staleness, band and trend for each differential."""

        result = self.tool_call('get_river_conditions')
        by_reach = {d['reach']: d for d in result['structuredContent']['differentials']}

        self.assertEqual(list(by_reach), ['isis', 'godstow', 'radley'])
        self.assertEqual(by_reach['isis']['value'], 0.12)
        self.assertEqual(by_reach['isis']['band'], 'High Green')
        self.assertFalse(by_reach['isis']['stale'])
        self.assertEqual(by_reach['isis']['trend'], 'rising')
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


    def test__sun_times(self):
        """Gives sun times for the requested date."""

        result = self.tool_call('get_river_conditions', {'date': '2026-03-29'})
        sun_times = result['structuredContent']['sun_times']

        self.assertEqual(sun_times['date'], '2026-03-29')
        self.assertEqual(sun_times['sunrise'], '2026-03-29T06:48:00+01:00')
        self.assertEqual(sun_times['sunset'], '2026-03-29T19:33:00+01:00')
        self.assertEqual(sun_times['first_boating'], '2026-03-29T05:48:00+01:00')
        self.assertEqual(sun_times['last_landing'], '2026-03-29T20:33:00+01:00')


    def test__sun_times__default_today(self):
        """Defaults to today's sun times."""

        result = self.tool_call('get_river_conditions')
        self.assertEqual(
            result['structuredContent']['sun_times']['date'],
            timezone.localdate().isoformat(),
        )


    def test__invalid_date(self):
        """Returns a tool-level error for a malformed date."""

        result = self.tool_call('get_river_conditions', {'date': 'tomorrow'})
        self.assertTrue(result['isError'])


class Test_Differential_trend(SimpleTestCase):

    def trend(self, earlier, now):
        reading = Differential(
            reach = Differential.Reach.ISIS,
            time = datetime(2026, 1, 1, 12, tzinfo = dt_timezone.utc),
            differential = now,
        )
        earliest = earlier and Differential(differential = earlier)
        with patch.object(Differential, 'objects') as objects:
            objects.using.return_value.filter.return_value.order_by.return_value.first.return_value = earliest  # noqa: E501
            return reading.trend

    def test__trend(self):
        """Compares against the earliest reading in the window, with a tolerance for noise."""

        self.assertEqual(self.trend(0.100, 0.120), 'rising')
        self.assertEqual(self.trend(0.120, 0.100), 'falling')
        self.assertEqual(self.trend(0.100, 0.105), 'steady')
        self.assertEqual(self.trend(0.105, 0.100), 'steady')
        self.assertIsNone(self.trend(None, 0.100))
