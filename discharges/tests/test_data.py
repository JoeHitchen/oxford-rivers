from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch
import logging
import zoneinfo

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from requests import HTTPError

from .. import data, models

logging.disable(logging.CRITICAL)

LONDON = zoneinfo.ZoneInfo('Europe/London')


def monitor(permit_number, status, changed = '2026-10-26T12:00:00'):
    """A record as returned by the Thames Water status endpoint."""
    return {
        'locationName': 'Test location',
        'permitNumber': permit_number,
        'locationGridRef': 'SP12345678',
        'x': 412345,
        'y': 212345,
        'receivingWaterCourse': 'Test Brook',
        'alertStatus': status,
        'statusChanged': changed,
        'alertPast48Hours': False,
        'uniqueId': 'TWL00000',
    }


class Test_ParseTime(TestCase):

    def test__winter(self):
        """Interprets timestamps as Europe/London time, i.e. UTC in winter."""

        parsed = data.parse_time('2026-10-26T12:30:00')

        self.assertEqual(parsed, datetime(2026, 10, 26, 12, 30, tzinfo = LONDON))
        self.assertEqual(parsed.utcoffset(), timedelta(0))


    def test__summer(self):
        """Interprets timestamps as Europe/London time, i.e. an hour ahead of UTC in summer."""

        parsed = data.parse_time('2026-07-01T12:30:00')

        self.assertEqual(parsed.utcoffset(), timedelta(hours = 1))


@patch('discharges.data.requests')
class Test_FetchDischarges(TestCase):

    def setUp(self):
        self.station = models.Station.objects.create(
            permit_number = 'TEST.0001',
            name = 'Test',
            watercourse = 'Test Brook',
            river = models.Station.Rivers.THAMES,
        )
        self.other = models.Station.objects.create(
            permit_number = 'TEST.0002',
            name = 'Other',
            watercourse = 'Other Brook',
            river = models.Station.Rivers.CHERWELL,
        )


    def respond(self, requests_mock, *monitors):
        requests_mock.get.return_value.ok = True
        requests_mock.get.return_value.json.return_value = {'items': list(monitors)}


    def test__new_discharge(self, requests_mock):
        """Creates an event for a monitor that has started discharging."""

        self.respond(
            requests_mock,
            monitor('TEST.0001', 'Discharging', '2026-10-26T10:15:00'),
            monitor('TEST.0002', 'Not discharging'),
        )

        stations = data.fetch_thames_water_discharges()

        self.assertEqual(stations, [self.station])
        event = self.station.events.get()
        self.assertEqual(event.start_at, datetime(2026, 10, 26, 10, 15, tzinfo = LONDON))
        self.assertAlmostEqual(
            event.start_seen.timestamp(), timezone.now().timestamp(), delta = 5,
        )
        self.assertIsNone(event.end_at)
        self.assertIsNone(event.end_seen)
        self.assertFalse(self.other.events.exists())
        requests_mock.get.assert_called_once()
        self.assertIn('/discharge/status', requests_mock.get.call_args.args[0])


    def test__continuing_discharge(self, requests_mock):
        """Advances the reading time of an event without creating another."""

        start_seen = timezone.now() - timedelta(hours = 1)
        self.station.events.create(
            start_at = datetime(2026, 10, 26, 10, 15, tzinfo = LONDON),
            start_seen = start_seen,
        )
        self.station.last_reading_at = start_seen
        self.station.save()
        self.respond(requests_mock, monitor('TEST.0001', 'Discharging', '2026-10-26T10:15:00'))

        data.fetch_thames_water_discharges()

        event = self.station.events.get()
        self.assertEqual(event.start_seen, start_seen)
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertGreater(self.station.last_reading_at, start_seen)
        self.assertEqual(event.latest_update_seen, self.station.last_reading_at)


    def test__end_of_discharge(self, requests_mock):
        """Ends an open event when the monitor reports no discharge."""

        self.station.events.create(start_at = datetime(2026, 10, 26, 10, 15, tzinfo = LONDON))
        self.respond(
            requests_mock,
            monitor('TEST.0001', 'Not discharging', '2026-10-26T11:45:00'),
        )

        stations = data.fetch_thames_water_discharges()

        self.assertEqual(stations, [])
        event = self.station.events.get()
        self.assertEqual(event.end_at, datetime(2026, 10, 26, 11, 45, tzinfo = LONDON))
        self.assertAlmostEqual(
            event.end_seen.timestamp(), timezone.now().timestamp(), delta = 5,
        )
        self.assertEqual(event.latest_update_seen, event.end_seen)


    def test__no_discharge(self, requests_mock):
        """Creates no events, but records the reading, for monitors that are not discharging."""

        self.respond(requests_mock, monitor('TEST.0001', 'Not discharging'))

        data.fetch_thames_water_discharges()

        self.assertFalse(models.DischargeEvent.objects.exists())
        self.station.refresh_from_db()
        self.assertIsNotNone(self.station.last_reading_at)


    def test__new_discharge_after_ended(self, requests_mock):
        """Starts a separate event for a discharge following an ended one."""

        self.station.events.create(
            start_at = datetime(2026, 10, 20, 10, 15, tzinfo = LONDON),
            end_at = datetime(2026, 10, 20, 12, 15, tzinfo = LONDON),
            end_seen = timezone.now() - timedelta(days = 6),
        )
        self.respond(requests_mock, monitor('TEST.0001', 'Discharging', '2026-10-26T10:15:00'))

        data.fetch_thames_water_discharges()

        self.assertEqual(self.station.events.count(), 2)
        self.assertEqual(self.station.events.active().count(), 1)


    def test__offline_ignored(self, requests_mock):
        """Leaves everything untouched, even an open event, when a monitor is offline."""

        last_reading = timezone.now() - timedelta(hours = 3)
        self.station.last_reading_at = last_reading
        self.station.save()
        event = self.station.events.create(
            start_at = datetime(2026, 10, 26, 10, 15, tzinfo = LONDON),
        )
        self.respond(
            requests_mock,
            monitor('TEST.0001', 'Offline', '2026-10-26T11:00:00'),
            monitor('TEST.0002', 'Offline'),
        )

        stations = data.fetch_thames_water_discharges()

        self.assertEqual(stations, [])
        event.refresh_from_db()
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertEqual(self.station.last_reading_at, last_reading)
        self.assertEqual(event.latest_update_seen, last_reading)
        self.other.refresh_from_db()
        self.assertIsNone(self.other.last_reading_at)
        self.assertTrue(models.Station.readings_out_of_date())


    def test__unmonitored_ignored(self, requests_mock):
        """Ignores monitors that are not stored as stations, and stations missing from the data."""

        self.respond(requests_mock, monitor('OTHER.9999', 'Discharging'))

        stations = data.fetch_thames_water_discharges()

        self.assertEqual(stations, [])
        self.assertFalse(models.DischargeEvent.objects.exists())
        self.assertEqual(models.Station.objects.count(), 2)


    def test__api_error(self, requests_mock):
        """Leaves existing records alone when the API errors, e.g. when over quota."""

        event = self.station.events.create(
            start_at = datetime(2026, 10, 26, 10, 15, tzinfo = LONDON),
        )
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = HTTPError('429')

        with self.assertRaises(HTTPError):
            data.fetch_thames_water_discharges()

        event.refresh_from_db()
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertIsNone(self.station.last_reading_at)


    def test__command(self, requests_mock):
        """Runs the retrieval from the management command."""

        self.respond(requests_mock, monitor('TEST.0001', 'Discharging'))

        call_command('fetch_thames_water_discharges', stdout = StringIO())

        self.assertEqual(self.station.events.count(), 1)
