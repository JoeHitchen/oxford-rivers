from datetime import timedelta
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

        self.thames = models.Station.objects.create(
            permit_number = 'TEST.0001',
            name = 'Thames Test',
            watercourse = 'Test Brook',
            river = models.Station.Rivers.THAMES,
            last_reading_at = self.right_now - timedelta(minutes = 5),
        )
        self.cherwell = models.Station.objects.create(
            permit_number = 'TEST.0002',
            name = 'Cherwell Test',
            watercourse = 'Cherwell Brook',
            river = models.Station.Rivers.CHERWELL,
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

    def test__empty(self, differentials_mock):
        """Explains that no discharges have been recorded, without claiming safety."""

        response = self.client.get(reverse('flags:index'))

        self.assertContains(response, 'Sewage Discharges')
        self.assertContains(response, 'No discharges recorded at the monitored stations')
        self.assertContains(response, 'does not mean the river is safe')
        self.assertEqual(len(response.context['discharge_events']), 0)


    def test__recent_events(self, differentials_mock):
        """Lists active events first, then recently ended ones, and omits older ones."""

        ended = self.make_event(self.thames, timedelta(hours = 20), timedelta(hours = 10))
        active = self.make_event(self.cherwell, timedelta(hours = 2))
        self.make_event(self.thames, timedelta(days = 5), timedelta(hours = 49))

        response = self.client.get(reverse('flags:index'))

        self.assertEqual(list(response.context['discharge_events']), [active, ended])
        self.assertContains(response, 'Cherwell Test')
        self.assertContains(response, 'Cherwell</td>')
        self.assertContains(response, 'Thames</td>')
        self.assertContains(response, 'table-danger', count = 1)
        self.assertContains(response, '<strong>Active</strong>', count = 1)


    def test__section_last(self, differentials_mock):
        """Places the discharges below the existing sections."""

        content = self.client.get(reverse('flags:index')).content.decode()

        self.assertGreater(content.index('Sewage Discharges'), content.index('EA Advisories</h2>'))


    def test__out_of_date(self, differentials_mock):
        """Warns when no readings have been retrieved recently."""

        response = self.client.get(reverse('flags:index'))
        self.assertNotContains(response, 'retrieve readings from Thames Water')

        models.Station.objects.update(last_reading_at = self.right_now - timedelta(hours = 3))
        response = self.client.get(reverse('flags:index'))
        self.assertContains(response, 'retrieve readings from Thames Water')


class Test_History(Base):

    def test__all_events(self):
        """Lists every event, newest first, however old."""

        old = self.make_event(self.thames, timedelta(days = 400), timedelta(days = 399))
        new = self.make_event(self.cherwell, timedelta(hours = 1))
        mid = self.make_event(self.thames, timedelta(days = 10), timedelta(days = 9))

        response = self.client.get(reverse('discharges:history'))

        self.assertEqual(list(response.context['page_obj']), [new, mid, old])
        self.assertContains(response, 'Start first seen')


    def test__station_filter(self):
        """Restricts to a single station when requested."""

        mine = self.make_event(self.thames, timedelta(hours = 5))
        self.make_event(self.cherwell, timedelta(hours = 1))

        response = self.client.get(
            reverse('discharges:history'),
            {'station': self.thames.permit_number},
        )

        self.assertEqual(list(response.context['page_obj']), [mine])
        self.assertContains(response, 'Show all stations')


    def test__unknown_station(self):
        """Responds with not found for an unknown station."""

        response = self.client.get(reverse('discharges:history'), {'station': 'NOPE.0000'})

        self.assertEqual(response.status_code, 404)


    def test__pagination(self):
        """Shows 100 events per page."""

        models.DischargeEvent.objects.bulk_create([
            models.DischargeEvent(
                station = self.thames,
                start_at = self.right_now - timedelta(hours = n + 1),
                end_at = self.right_now - timedelta(hours = n),
            )
            for n in range(101)
        ])

        first = self.client.get(reverse('discharges:history'))
        second = self.client.get(reverse('discharges:history'), {'page': 2})

        self.assertEqual(len(first.context['page_obj']), 100)
        self.assertEqual(len(second.context['page_obj']), 1)
        self.assertContains(first, 'Page 1 of 2')


    def test__empty(self):
        """Handles there being no events."""

        response = self.client.get(reverse('discharges:history'))

        self.assertContains(response, 'No discharges have been recorded.')


    def test__nav(self):
        """Links to the history from the navigation bar."""

        response = self.client.get(reverse('discharges:history'))

        self.assertContains(response, 'href="{}"'.format(reverse('discharges:history')))
