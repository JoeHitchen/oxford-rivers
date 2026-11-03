from datetime import timedelta

from django.test import TestCase
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
            'stations_discharging': 0,
            'percentage_discharging': 0,
            'readings_out_of_date': True,
        })


    def test__counts(self):
        """Counts discharging, online and offline stations, with percentages."""

        recent = timedelta(minutes = 10)
        for n in range(1, 4):
            self.make_station(n, recent, discharging = (n == 1))
        self.make_station(4, recent)
        self.make_station(5, timedelta(hours = 3))
        self.make_station(6)  # Never read

        self.assertEqual(models.Station.summary(), {
            'stations_total': 6,
            'stations_offline': 2,
            'percentage_offline': 33,
            'stations_online': 4,
            'stations_discharging': 1,
            'percentage_discharging': 25,
            'readings_out_of_date': False,
        })


    def test__online_window(self):
        """Considers stations online until their last reading is more than two hours old."""

        self.make_station(1, timedelta(hours = 1, minutes = 59))
        self.make_station(2, timedelta(hours = 2, minutes = 1))

        result = models.Station.summary()

        self.assertEqual(result['stations_online'], 1)
        self.assertEqual(result['stations_offline'], 1)


    def test__ended_events_not_discharging(self):
        """Does not count stations whose events have all ended."""

        station = self.make_station(1, timedelta(minutes = 10))
        station.events.create(
            start_at = timezone.now() - timedelta(hours = 3),
            end_at = timezone.now() - timedelta(hours = 1),
        )

        self.assertEqual(models.Station.summary()['stations_discharging'], 0)


    def test__held_discharge(self):
        """Holds a station as online and discharging if it goes quiet mid-discharge."""

        self.make_station(1, timedelta(hours = 3), discharging = True)
        self.make_station(2, timedelta(minutes = 10))

        result = models.Station.summary()

        self.assertEqual(result['stations_discharging'], 1)
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
        self.assertEqual(result['stations_discharging'], 0)


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
