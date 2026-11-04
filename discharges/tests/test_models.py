from datetime import timedelta

from django.test import TestCase, tag
from django.utils import timezone

from .. import models


class Test_Station_Summary(TestCase):

    def make_station(self, n, reading_age = None, discharging = False):
        """A station last read `reading_age` ago, if ever."""
        station = models.Station.objects.create(
            permit_number = 'TEST.{:04d}'.format(n),
            name = 'Test {}'.format(n),
            watercourse = 'Test Brook',
            river = models.Station.Rivers.THAMES,
            last_reading_at = reading_age and timezone.now() - reading_age,
        )
        if discharging:
            station.events.create(start_at = timezone.now() - timedelta(hours = 1))
        return station


    def test__no_stations(self):
        """Reports zeros when there are no stations."""

        result = models.Station.summary()

        self.assertEqual(result, {
            'stations_total': 0,
            'stations_offline': 0,
            'percentage_offline': 0,
            'stations_online': 0,
            'stations_actively_discharging': 0,
            'percentage_actively_discharging': 0,
            'stations_discharged_recently': 0,
            'percentage_discharged_recently': 0,
            'recent_window_hours': 48,
            'readings_out_of_date': True,
        })


    def test__counts(self):
        """Counts discharging, online and offline stations, with percentages."""

        recent = timedelta(minutes = 10)
        self.make_station(1, recent, discharging = True)
        self.make_station(2, recent).events.create(
            start_at = timezone.now() - timedelta(hours = 3),
            end_at = timezone.now() - timedelta(hours = 1),
        )
        self.make_station(3, recent)
        self.make_station(4, recent)
        self.make_station(5, timedelta(hours = 3))
        self.make_station(6)  # Never read

        self.assertEqual(models.Station.summary(), {
            'stations_total': 6,
            'stations_offline': 2,
            'percentage_offline': 33,
            'stations_online': 4,
            'stations_actively_discharging': 1,
            'percentage_actively_discharging': 25,
            'stations_discharged_recently': 2,
            'percentage_discharged_recently': 50,
            'recent_window_hours': 48,
            'readings_out_of_date': False,
        })


    def test__online_window(self):
        """Considers stations online until their last reading is more than two hours old."""

        self.make_station(1, timedelta(hours = 1, minutes = 59))
        self.make_station(2, timedelta(hours = 2, minutes = 1))

        result = models.Station.summary()

        self.assertEqual(result['stations_online'], 1)
        self.assertEqual(result['stations_offline'], 1)


    def test__ended_events_not_actively_discharging(self):
        """Does not count stations whose events have all ended as actively discharging."""

        station = self.make_station(1, timedelta(minutes = 10))
        station.events.create(
            start_at = timezone.now() - timedelta(hours = 3),
            end_at = timezone.now() - timedelta(hours = 1),
        )

        result = models.Station.summary()

        self.assertEqual(result['stations_actively_discharging'], 0)
        self.assertEqual(result['stations_discharged_recently'], 1)


    def test__held_discharge(self):
        """Holds a station as online and discharging if it goes quiet mid-discharge."""

        self.make_station(1, timedelta(hours = 3), discharging = True)
        self.make_station(2, timedelta(minutes = 10))

        result = models.Station.summary()

        self.assertEqual(result['stations_actively_discharging'], 1)
        self.assertEqual(result['stations_online'], 2)
        self.assertEqual(result['stations_offline'], 0)


    def test__recent_window(self):
        """Keeps a quiet station online, but not discharging, until its last discharge is old.

        We know there has been a discharge in the window, so the station is not a blind spot.
        """

        inside = self.make_station(1, timedelta(hours = 60))
        inside.events.create(
            start_at = timezone.now() - timedelta(hours = 50),
            end_at = timezone.now() - timedelta(hours = 47),
        )
        outside = self.make_station(2, timedelta(hours = 60))
        outside.events.create(
            start_at = timezone.now() - timedelta(hours = 52),
            end_at = timezone.now() - timedelta(hours = 49),
        )

        result = models.Station.summary()

        self.assertEqual(result['stations_online'], 1)
        self.assertEqual(result['stations_offline'], 1)
        self.assertEqual(result['stations_actively_discharging'], 0)
        self.assertEqual(result['stations_discharged_recently'], 1)


    def test__readings_out_of_date(self):
        """Is out of date once the newest reading is more than two hours old."""

        station = self.make_station(1)

        for age, expected in (
            (timedelta(hours = 1, minutes = 59), False),
            (timedelta(hours = 2, minutes = 1), True),
        ):
            with self.subTest(age = age):
                station.last_reading_at = timezone.now() - age
                station.save()

                self.assertEqual(models.Station.summary()['readings_out_of_date'], expected)


    def test__readings_out_of_date__newest_reading(self):
        """Is based on the newest reading, so a long-offline station does not matter."""

        self.make_station(1, timedelta(minutes = 20))
        self.make_station(2, timedelta(days = 4))

        self.assertFalse(models.Station.summary()['readings_out_of_date'])


class Test_Station_UpdateDischargeStatus(TestCase):

    def setUp(self):
        self.right_now = timezone.now()
        self.station = models.Station.objects.create(
            permit_number = 'TEST.0001',
            name = 'Test',
            watercourse = 'Test Brook',
            river = models.Station.Rivers.THAMES,
        )


    def make_event(self, started_ago, last_reading_ago):
        self.station.last_reading_at = self.right_now - last_reading_ago
        self.station.save()
        return self.station.events.create(
            start_at = self.right_now - started_ago,
            start_seen = self.right_now - started_ago,
        )


    def assert_read_just_now(self):
        self.station.refresh_from_db()
        self.assertAlmostEqual(
            self.station.last_reading_at.timestamp(), timezone.now().timestamp(), delta = 5,
        )


    def test__discharging(self):
        """Starts a discharge at the reported time, recording the reading."""

        reported = self.right_now - timedelta(hours = 1)

        self.station.update_discharge_status('Discharging', reported)

        event = self.station.events.get()
        self.assertEqual(event.start_at, reported)
        self.assertAlmostEqual(
            event.start_seen.timestamp(), timezone.now().timestamp(), delta = 5,
        )
        self.assertIsNone(event.end_at)
        self.assert_read_just_now()


    def test__still_discharging(self):
        """Continues an active discharge unchanged, only advancing the reading."""

        original = self.make_event(timedelta(hours = 3), timedelta(hours = 1))
        previous_reading = self.station.last_reading_at

        self.station.update_discharge_status('Discharging', self.right_now)

        event = self.station.events.get()
        self.assertEqual(event.pk, original.pk)
        self.assertEqual(event.start_at, original.start_at)
        self.assertEqual(event.start_seen, original.start_seen)
        self.assertIsNone(event.end_at)
        self.station.refresh_from_db()
        self.assertGreater(self.station.last_reading_at, previous_reading)


    def test__not_discharging(self):
        """Ends an active discharge at the reported time, recording the reading."""

        event = self.make_event(timedelta(hours = 3), timedelta(hours = 1))
        reported = self.right_now - timedelta(minutes = 30)

        self.station.update_discharge_status('Not discharging', reported)

        event.refresh_from_db()
        self.assertEqual(event.end_at, reported)
        self.assertAlmostEqual(
            event.end_seen.timestamp(), timezone.now().timestamp(), delta = 5,
        )
        self.assert_read_just_now()


    def test__not_discharging__nothing_active(self):
        """Creates nothing for a station that was not discharging, but records the reading."""

        self.station.update_discharge_status('Not discharging', self.right_now)

        self.assertFalse(self.station.events.exists())
        self.assert_read_just_now()


    def test__offline(self):
        """Ignores an offline station entirely, leaving any discharge and reading as they were."""

        event = self.make_event(timedelta(hours = 3), timedelta(hours = 1))
        previous_reading = self.station.last_reading_at

        for status in ('Offline', None):
            self.station.update_discharge_status(status, self.right_now)

            event.refresh_from_db()
            self.assertIsNone(event.end_at)
            self.station.refresh_from_db()
            self.assertEqual(self.station.last_reading_at, previous_reading)


    def test__within_window(self):
        """Leaves an active discharge open while it was seen within the recent window."""

        event = self.make_event(timedelta(days = 4), timedelta(hours = 47))

        self.station.update_discharge_status()

        event.refresh_from_db()
        self.assertIsNone(event.end_at)
        self.assertIsNone(event.end_seen)


    def test__outside_window(self):
        """Closes an active discharge as of the last time it was seen once outside the window."""

        event = self.make_event(timedelta(days = 4), timedelta(hours = 49))
        last_reading = self.station.last_reading_at

        self.station.update_discharge_status()

        event.refresh_from_db()
        self.assertEqual(event.end_at, last_reading)
        self.assertEqual(event.end_seen, last_reading)
        self.assertNotIn(event, models.DischargeEvent.recent_discharges())


class Test_DischargeEvent(TestCase):

    def setUp(self):
        self.right_now = timezone.now()
        self.station = models.Station.objects.create(
            permit_number = 'TEST.0001',
            name = 'Test',
            watercourse = 'Test Brook',
            river = models.Station.Rivers.THAMES,
            last_reading_at = self.right_now - timedelta(minutes = 10),
        )


    def make_event(self, start_ago, end_ago = None):
        return self.station.events.create(
            start_at = self.right_now - start_ago,
            start_seen = self.right_now - start_ago + timedelta(minutes = 5),
            end_at = end_ago and self.right_now - end_ago,
            end_seen = end_ago and self.right_now - end_ago + timedelta(minutes = 5),
        )


    def test__latest_update_seen__active(self):
        """Uses the station's last reading for an active event."""

        event = self.make_event(timedelta(hours = 3))

        self.assertTrue(event.is_active)
        self.assertEqual(event.latest_update_seen, self.station.last_reading_at)


    def test__latest_update_seen__ended(self):
        """Uses when the end was seen for an ended event, whatever the station does later."""

        event = self.make_event(timedelta(hours = 3), timedelta(hours = 1))
        self.station.last_reading_at = self.right_now
        self.station.save()

        self.assertFalse(event.is_active)
        self.assertEqual(event.latest_update_seen, event.end_seen)


    def test__styling(self):
        """Colours active events red, those that ended in the recent window amber, others not."""

        active = self.make_event(timedelta(days = 5))
        recent = self.make_event(timedelta(hours = 60), timedelta(hours = 47))
        old = self.make_event(timedelta(days = 4), timedelta(hours = 49))

        self.assertEqual(active.styling(), 'table-danger')
        self.assertEqual(recent.styling(), 'table-warning')
        self.assertEqual(old.styling(), '')


    def test__recent_discharges(self):
        """Lists active events first, then ended ones, each newest first, omitting old ones."""

        ended_old = self.make_event(timedelta(hours = 45), timedelta(hours = 30))
        ended_new = self.make_event(timedelta(hours = 5), timedelta(hours = 1))
        active_new = self.make_event(timedelta(hours = 3))
        active_old = self.make_event(timedelta(days = 5))
        self.make_event(timedelta(days = 4), timedelta(hours = 49))

        events = list(models.DischargeEvent.recent_discharges())

        self.assertEqual(events, [active_new, active_old, ended_new, ended_old])


    @tag('query-count')
    def test__recent_discharges__query_count(self):
        """Expect:
            (1) SELECT recent events, with their stations
        """

        self.make_event(timedelta(hours = 3))
        self.make_event(timedelta(hours = 5), timedelta(hours = 1))

        with self.assertNumQueries(1):
            [event.station.name for event in models.DischargeEvent.recent_discharges()]
