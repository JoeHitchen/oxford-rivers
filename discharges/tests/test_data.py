from datetime import datetime, timedelta, timezone as dt_timezone
from io import StringIO
from unittest.mock import patch
import logging

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from requests import HTTPError

from .. import data, models, tasks

logging.disable(logging.CRITICAL)

UTC = dt_timezone.utc


def report(permit_number, status, changed = '2026-10-26T12:00:00'):
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


    def respond(self, requests_mock, *reports):
        requests_mock.get.return_value.ok = True
        requests_mock.get.return_value.json.return_value = {'items': list(reports)}


    def make_stale_event(self, last_reading_ago):
        self.station.last_reading_at = timezone.now() - last_reading_ago
        self.station.save()
        return self.station.events.create(
            start_at = datetime(2026, 10, 20, 10, 15, tzinfo = UTC),
            start_seen = timezone.now() - timedelta(days = 6),
        )


    def test__api_error(self, requests_mock):
        """Leaves existing records alone when the API errors, e.g. when over quota."""

        event = self.station.events.create(
            start_at = datetime(2026, 10, 26, 10, 15, tzinfo = UTC),
        )
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = HTTPError('429')

        with self.assertRaises(HTTPError):
            data.fetch_thames_water_discharges()

        event.refresh_from_db()
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertIsNone(self.station.last_reading_at)


    def test__ignore_unmonitored_stations(self, requests_mock):
        """Ignores reports for stations that are not stored, and stations with no report."""

        self.respond(requests_mock, report('OTHER.9999', 'Discharging'))

        result = data.fetch_thames_water_discharges()

        self.assertEqual(result['stations_actively_discharging'], 0)
        self.assertEqual(result['stations_online'], 0)
        self.assertEqual(result['stations_offline'], 2)  # Never read
        self.assertFalse(models.DischargeEvent.objects.exists())
        self.assertEqual(models.Station.objects.count(), 2)


    def test__skip_bad_data(self, requests_mock):
        """Skips a station with a bad report, and carries on with the rest.

        Stations are processed by name, so 'Other', which has the bad report, comes before 'Test'.
        """

        no_status = report('TEST.0002', 'Discharging')
        del no_status['alertStatus']

        for label, bad_report in (
            ('no timestamp', report('TEST.0002', 'Discharging', None)),
            ('bad timestamp', report('TEST.0002', 'Discharging', 'last Tuesday')),
            ('no status', no_status),
        ):
            with self.subTest(label):
                models.DischargeEvent.objects.all().delete()
                self.respond(
                    requests_mock,
                    bad_report,
                    {'alertStatus': 'Discharging'},  # No permit number to match
                    report('TEST.0001', 'Discharging', '2026-10-26T10:15:00'),
                )

                result = data.fetch_thames_water_discharges()

                self.assertFalse(self.other.events.exists())
                self.assertEqual(self.station.events.count(), 1)
                self.assertEqual(result['stations_actively_discharging'], 1)
        self.other.refresh_from_db()
        self.assertIsNone(self.other.last_reading_at)


    def test__no_discharge(self, requests_mock):
        """Creates no events, but records the reading, for stations that are not discharging."""

        self.respond(requests_mock, report('TEST.0001', 'Not discharging'))

        data.fetch_thames_water_discharges()

        self.assertFalse(models.DischargeEvent.objects.exists())
        self.station.refresh_from_db()
        self.assertIsNotNone(self.station.last_reading_at)


    def test__new_discharge(self, requests_mock):
        """Creates an event for a station that has started discharging."""

        self.respond(
            requests_mock,
            report('TEST.0001', 'Discharging', '2026-10-26T10:15:00'),
            report('TEST.0002', 'Not discharging'),
        )

        result = data.fetch_thames_water_discharges()

        self.assertEqual(result['stations_actively_discharging'], 1)
        event = self.station.events.get()
        self.assertEqual(event.start_at, datetime(2026, 10, 26, 10, 15, tzinfo = UTC))
        self.assertAlmostEqual(
            event.start_seen.timestamp(), timezone.now().timestamp(), delta = 5,
        )
        self.assertIsNone(event.end_at)
        self.assertIsNone(event.end_seen)
        self.assertFalse(self.other.events.exists())
        requests_mock.get.assert_called_once()
        self.assertIn('/discharge/status', requests_mock.get.call_args.args[0])


    def test__continuing_discharge(self, requests_mock):
        """Continues a discharge, even after its station has been quiet, without a new event."""

        start_seen = timezone.now() - timedelta(hours = 5)
        self.station.events.create(
            start_at = datetime(2026, 10, 26, 10, 15, tzinfo = UTC),
            start_seen = start_seen,
        )
        quiet_since = timezone.now() - timedelta(hours = 3)
        self.station.last_reading_at = quiet_since
        self.station.save()
        self.respond(requests_mock, report('TEST.0001', 'Discharging', '2026-10-26T10:15:00'))

        result = data.fetch_thames_water_discharges()

        event = self.station.events.get()
        self.assertEqual(event.start_seen, start_seen)
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertGreater(self.station.last_reading_at, quiet_since)
        self.assertEqual(result['stations_actively_discharging'], 1)


    def test__end_of_discharge(self, requests_mock):
        """Ends an open event when the station reports no discharge."""

        self.station.events.create(start_at = datetime(2026, 10, 26, 10, 15, tzinfo = UTC))
        self.respond(
            requests_mock,
            report('TEST.0001', 'Not discharging', '2026-10-26T11:45:00'),
        )

        result = data.fetch_thames_water_discharges()

        event = self.station.events.get()
        self.assertEqual(event.end_at, datetime(2026, 10, 26, 11, 45, tzinfo = UTC))
        self.assertAlmostEqual(
            event.end_seen.timestamp(), timezone.now().timestamp(), delta = 5,
        )
        self.assertEqual(result['stations_actively_discharging'], 0)


    def test__new_discharge_after_ended(self, requests_mock):
        """Starts a separate event for a discharge following an ended one."""

        self.station.events.create(
            start_at = datetime(2026, 10, 20, 10, 15, tzinfo = UTC),
            end_at = datetime(2026, 10, 20, 12, 15, tzinfo = UTC),
            end_seen = timezone.now() - timedelta(days = 6),
        )
        self.respond(requests_mock, report('TEST.0001', 'Discharging', '2026-10-26T10:15:00'))

        data.fetch_thames_water_discharges()

        self.assertEqual(self.station.events.count(), 2)
        self.assertEqual(self.station.events.filter(end_at__isnull = True).count(), 1)


    def test__offline__temporarily(self, requests_mock):
        """Leaves everything untouched, even an open event, when a station is offline."""

        last_reading = timezone.now() - timedelta(hours = 3)
        self.station.last_reading_at = last_reading
        self.station.save()
        event = self.station.events.create(
            start_at = datetime(2026, 10, 26, 10, 15, tzinfo = UTC),
        )
        self.respond(
            requests_mock,
            report('TEST.0001', 'Offline', '2026-10-26T11:00:00'),
            report('TEST.0002', 'Offline'),
        )

        result = data.fetch_thames_water_discharges()

        event.refresh_from_db()
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertEqual(self.station.last_reading_at, last_reading)
        self.other.refresh_from_db()
        self.assertIsNone(self.other.last_reading_at)
        self.assertEqual(result['stations_actively_discharging'], 1)  # Held, as seen recently
        self.assertTrue(result['readings_out_of_date'])


    def test__offline__returns_not_discharging(self, requests_mock):
        """Ends a held discharge at the reported time when it returns in time."""

        event = self.make_stale_event(timedelta(hours = 10))
        self.respond(
            requests_mock,
            report('TEST.0001', 'Not discharging', '2026-10-26T11:45:00'),
        )

        data.fetch_thames_water_discharges()

        event.refresh_from_db()
        self.assertEqual(event.end_at, datetime(2026, 10, 26, 11, 45, tzinfo = UTC))


    def test__offline__returns_discharging(self, requests_mock):
        """Starts a new discharge, rather than extending the lost one, when a station returns."""

        lost = self.make_stale_event(timedelta(hours = 50))
        self.respond(requests_mock)
        data.fetch_thames_water_discharges()  # Silent poll closes the lost discharge
        self.respond(requests_mock, report('TEST.0001', 'Discharging', '2026-10-26T10:15:00'))

        result = data.fetch_thames_water_discharges()

        lost.refresh_from_db()
        self.assertIsNotNone(lost.end_at)
        self.assertEqual(self.station.events.count(), 2)
        self.assertEqual(self.station.events.filter(end_at__isnull = True).count(), 1)
        self.assertEqual(result['stations_actively_discharging'], 1)


    def test__offline__closes_lost_discharge(self, requests_mock):
        """Closes a discharge once its station has been offline beyond the recent window."""

        event = self.make_stale_event(timedelta(hours = 50))
        self.respond(requests_mock, report('TEST.0001', 'Offline'))

        result = data.fetch_thames_water_discharges()

        event.refresh_from_db()
        self.assertIsNotNone(event.end_at)
        self.assertEqual(result['stations_actively_discharging'], 0)


    def test__offline__closes_dropped_station(self, requests_mock):
        """Also closes it if the station has dropped out of the Thames Water data."""

        event = self.make_stale_event(timedelta(hours = 50))
        self.respond(requests_mock)

        data.fetch_thames_water_discharges()

        event.refresh_from_db()
        self.assertIsNotNone(event.end_at)


    def test__utc_timestamps(self, requests_mock):
        """Reads the timestamps as UTC, whatever the season, as they have no offset."""

        self.respond(requests_mock, report('TEST.0001', 'Discharging', '2026-07-01T12:00:00'))

        data.fetch_thames_water_discharges()

        event = self.station.events.get()
        self.assertEqual(event.start_at, datetime(2026, 7, 1, 12, 0, tzinfo = UTC))
        self.assertEqual(timezone.localtime(event.start_at).hour, 13)  # BST


    def test__command(self, requests_mock):
        """Runs the retrieval from the management command."""

        self.respond(requests_mock, report('TEST.0001', 'Discharging'))

        call_command('fetch_thames_water_discharges', stdout = StringIO())

        self.assertEqual(self.station.events.count(), 1)


    def test__task(self, requests_mock):
        """Runs the retrieval from the Celery task, returning the summary."""

        self.respond(requests_mock, report('TEST.0001', 'Discharging'))

        result = tasks.fetch_thames_water_discharges()

        self.assertEqual(self.station.events.count(), 1)
        self.assertEqual(result['stations_actively_discharging'], 1)
