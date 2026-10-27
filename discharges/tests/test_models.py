from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .. import models


class Test_Fixture(TestCase):
    fixtures = ['stations']
    
    def test__stations_loaded(self):
        """Loads the monitored stations with unique permit numbers and valid rivers."""
        
        stations = models.Station.objects.all()
        self.assertTrue(stations.exists())
        self.assertEqual(
            stations.count(),
            len({station.permit_number for station in stations}),
        )
        for station in stations:
            self.assertIn(station.river, models.Station.Rivers.values)
    
    
    def test__rivers_distinguished(self):
        """Includes Cherwell and Seacourt Stream stations as well as the Thames."""
        
        rivers = set(models.Station.objects.values_list('river', flat = True))
        self.assertEqual(rivers, set(models.Station.Rivers.values))


class Test_Station(TestCase):
    
    def setUp(self):
        self.right_now = timezone.now()
        self.station = models.Station.objects.create(
            permit_number = 'TEST.0001',
            name = 'Test',
            watercourse = 'Test Brook',
            river = models.Station.Rivers.THAMES,
        )
    
    
    def test__out_of_date__never_read(self):
        """Considers readings out of date when no station has ever been read."""
        self.assertTrue(models.Station.readings_out_of_date())
    
    
    def test__out_of_date__newest_reading(self):
        """Is based on the newest reading, so a long-offline station does not matter."""
        
        models.Station.objects.create(
            permit_number = 'TEST.0002',
            name = 'Other',
            watercourse = 'Other Brook',
            river = models.Station.Rivers.CHERWELL,
            last_reading_at = self.right_now - timedelta(minutes = 20),
        )
        self.station.last_reading_at = self.right_now - timedelta(days = 4)
        self.station.save()
        
        self.assertFalse(models.Station.readings_out_of_date())
    
    
    def test__out_of_date__all_stale(self):
        """Is out of date when every station's last reading is over two hours old."""
        
        self.station.last_reading_at = self.right_now - timedelta(hours = 2, minutes = 1)
        self.station.save()
        
        self.assertTrue(models.Station.readings_out_of_date())


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
        
        self.assertFalse(event.is_active)
        self.assertEqual(event.latest_update_seen, event.end_seen)
    
    
    def test__duration(self):
        """Measures from start to end, or to now for active events."""
        
        ended = self.make_event(timedelta(hours = 3), timedelta(hours = 1))
        active = self.make_event(timedelta(hours = 3))
        
        self.assertEqual(ended.duration, timedelta(hours = 2))
        self.assertAlmostEqual(
            active.duration.total_seconds(),
            timedelta(hours = 3).total_seconds(),
            delta = 5,
        )
    
    
    def test__querysets(self):
        """Selects active events, and active or recently-ended events."""
        
        active = self.make_event(timedelta(days = 5))
        recent = self.make_event(timedelta(hours = 60), timedelta(hours = 47))
        old = self.make_event(timedelta(days = 4), timedelta(hours = 49))
        
        self.assertEqual(list(models.DischargeEvent.objects.active()), [active])
        self.assertEqual(
            set(models.DischargeEvent.objects.recent()),
            {active, recent},
        )
        self.assertNotIn(old, models.DischargeEvent.objects.recent())
