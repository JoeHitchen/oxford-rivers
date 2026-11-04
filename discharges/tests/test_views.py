from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from flags import models as flag_models

from .. import models


class Base(TestCase):
    fixtures = ['flags']

    def setUp(self):
        self.right_now = timezone.now()
        for reach in flag_models.Reach.objects.filter(has_ourcs_flag = True):
            reach.statuses.create(flag = flag_models.Status.Flags.GREEN, set_at = self.right_now)
        for reach in flag_models.Reach.objects.all():
            reach.advisories.create(board = flag_models.Advisory.Boards.NONE)

        self.thames = self.make_station('Thames Test', models.Station.Rivers.THAMES)
        self.cherwell = self.make_station('Cherwell Test', models.Station.Rivers.CHERWELL)


    def make_station(self, name, river):
        return models.Station.objects.create(
            permit_number = name.upper().replace(' ', '.'),
            name = name,
            watercourse = 'Test Brook',
            river = river,
            last_reading_at = self.right_now - timedelta(minutes = 5),
        )


    def make_event(self, station, start_ago, end_ago = None):
        return station.events.create(
            start_at = self.right_now - start_ago,
            start_seen = self.right_now - start_ago,
            end_at = end_ago and self.right_now - end_ago,
            end_seen = end_ago and self.right_now - end_ago,
        )


@patch('flags.views.jameson.Differential.latest_by_reach', return_value = [])
class Test_Index(Base):

    def test__summary(self, differentials_mock):
        """Shows the number and percentage of stations discharging, recently so, and offline."""

        self.cherwell.last_reading_at = self.right_now - timedelta(hours = 3)
        self.cherwell.save()
        extra = self.make_station('Extra Test', models.Station.Rivers.THAMES)
        spare = self.make_station('Spare Test', models.Station.Rivers.THAMES)
        self.make_station('Quiet Test', models.Station.Rivers.THAMES)
        self.make_event(self.thames, timedelta(hours = 2))
        self.make_event(extra, timedelta(hours = 2))
        self.make_event(spare, timedelta(hours = 6), timedelta(hours = 4))

        response = self.client.get(reverse('flags:index'))

        summary = response.context['discharge_summary']
        self.assertEqual(summary['stations_actively_discharging'], 2)
        self.assertEqual(summary['stations_discharged_recently'], 3)
        self.assertEqual(summary['stations_offline'], 1)
        self.assertContains(response, 'Discharged within 48h')
        self.assertContains(response, '2&ensp;(50%)')  # Of the four online stations
        self.assertContains(response, '3&ensp;(75%)')
        self.assertContains(response, '1&ensp;(20%)')  # Of all five stations


    def test__out_of_date(self, differentials_mock):
        """Warns when no readings have been retrieved recently."""

        response = self.client.get(reverse('flags:index'))
        self.assertNotContains(response, 'retrieve readings from Thames Water')

        models.Station.objects.update(last_reading_at = self.right_now - timedelta(hours = 3))
        response = self.client.get(reverse('flags:index'))
        self.assertContains(response, 'retrieve readings from Thames Water')

    def test__events__empty(self, differentials_mock):
        """Explains that no discharges have been recorded, without claiming safety."""

        response = self.client.get(reverse('flags:index'))

        self.assertContains(response, 'No discharges recorded at the monitored stations')
        self.assertContains(response, 'should not be taken to mean the river water is clean')
        self.assertEqual(len(response.context['discharge_events']), 0)


    def test__events__ordering(self, differentials_mock):
        """Lists active events first, then recently ended ones, and omits older ones."""

        old = self.make_station('Old Test', models.Station.Rivers.THAMES)
        ended = self.make_event(self.thames, timedelta(hours = 20), timedelta(hours = 10))
        active = self.make_event(self.cherwell, timedelta(hours = 2))
        self.make_event(old, timedelta(days = 5), timedelta(hours = 49))

        response = self.client.get(reverse('flags:index'))

        self.assertEqual(list(response.context['discharge_events']), [active, ended])
        self.assertContains(response, 'Cherwell Test')
        self.assertContains(response, 'Thames Test')
        self.assertNotContains(response, 'Old Test')
        self.assertContains(response, 'View all discharges')


    def test__events__capping(self, differentials_mock):
        """Shows only the first ten events: active first, then the most recently ended."""

        active = self.make_event(self.cherwell, timedelta(hours = 50))
        ended = [
            self.make_event(self.thames, timedelta(hours = 20 + n), timedelta(hours = 10 + n))
            for n in range(12)
        ]

        response = self.client.get(reverse('flags:index'))

        self.assertEqual(list(response.context['discharge_events']), [active] + ended[:9])


    def test__events__styling(self, differentials_mock):
        """Highlights active events in red and recently ended events in amber."""

        self.make_event(self.thames, timedelta(hours = 20), timedelta(hours = 10))
        self.make_event(self.cherwell, timedelta(hours = 2))

        response = self.client.get(reverse('flags:index'))

        self.assertContains(response, 'table-danger', count = 1)
        self.assertContains(response, 'table-warning', count = 1)


class Test_History(Base):

    def test__summary_content(self):
        """Shows the headline numbers, and warns when no readings have been retrieved recently."""

        response = self.client.get(reverse('discharges:history'))
        self.assertEqual(response.context['discharge_summary']['stations_total'], 2)
        self.assertNotContains(response, 'retrieve readings from Thames Water')

        models.Station.objects.update(last_reading_at = self.right_now - timedelta(hours = 3))
        response = self.client.get(reverse('discharges:history'))
        self.assertContains(response, 'retrieve readings from Thames Water')


    def test__no_events(self):
        """Handles there being no events."""

        response = self.client.get(reverse('discharges:history'))
        self.assertContains(response, 'No discharges have been recorded.')


    def test__event_ordering(self):
        """Lists every event, newest first, however old."""

        old = self.make_event(self.thames, timedelta(days = 400), timedelta(days = 399))
        new = self.make_event(self.cherwell, timedelta(hours = 1))
        mid = self.make_event(self.thames, timedelta(days = 10), timedelta(days = 9))

        response = self.client.get(reverse('discharges:history'))

        self.assertEqual(list(response.context['page_obj']), [new, mid, old])


    def test__pagination(self):
        """Shows 50 events per page, continuing in order onto the next page."""

        models.DischargeEvent.objects.bulk_create([
            models.DischargeEvent(
                station = self.thames,
                start_at = self.right_now - timedelta(hours = n + 1),
                end_at = self.right_now - timedelta(hours = n),
            )
            for n in range(51)
        ])

        first = self.client.get(reverse('discharges:history'))
        second = self.client.get(reverse('discharges:history'), {'page': 2})

        self.assertEqual(len(first.context['page_obj']), 50)
        self.assertEqual(len(second.context['page_obj']), 1)
        self.assertEqual(
            second.context['page_obj'][0],
            models.DischargeEvent.objects.order_by('start_at').first(),
        )


    def test__last_seen(self):
        """Shows when each discharge was last seen, whether it is still active or has ended."""

        self.thames.last_reading_at = datetime(2026, 7, 1, 12, 30, tzinfo = dt_timezone.utc)
        self.thames.save()
        self.make_event(self.thames, timedelta(hours = 3))
        self.cherwell.events.create(
            start_at = datetime(2026, 6, 30, 6, 0, tzinfo = dt_timezone.utc),
            end_at = datetime(2026, 6, 30, 8, 30, tzinfo = dt_timezone.utc),
            end_seen = datetime(2026, 6, 30, 8, 45, tzinfo = dt_timezone.utc),
        )

        response = self.client.get(reverse('discharges:history'))

        self.assertContains(response, '01/07/2026 13:30')  # Rendered in local time (BST)
        self.assertContains(response, '30/06/2026 09:45')


    def test__colouring(self):
        """Colours active and recent events, but not those that ended before the recent window."""

        old = self.make_station('Old Test', models.Station.Rivers.THAMES)
        self.make_event(old, timedelta(days = 400), timedelta(days = 399))
        self.make_event(self.thames, timedelta(days = 10), timedelta(hours = 10))
        self.make_event(self.cherwell, timedelta(hours = 1))

        response = self.client.get(reverse('discharges:history'))

        self.assertContains(response, 'table-danger', count = 1)
        self.assertContains(response, 'table-warning', count = 1)

