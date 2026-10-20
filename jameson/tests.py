from django.test import SimpleTestCase

from . import bands
from .models import Differential


class Test_Bands(SimpleTestCase):
    
    def test__isis(self):
        """Names the band containing each differential, including the exact boundaries."""
        
        cases = [
            (-0.1, 'Low green'),
            (0.099, 'Low green'),
            (0.100, 'High green'),
            (0.195, 'Green/blue borderline'),
            (0.215, 'Green/blue borderline'),
            (0.235, 'Low blue'),
            (0.360, 'High blue'),
            (0.442, 'Blue/amber borderline'),
            (0.500, 'Amber'),
            (0.535, 'Amber/red borderline'),
            (0.600, 'Low red'),
            (0.650, 'High red'),
            (0.720, 'Red/black borderline'),
            (0.740, 'Black'),
            (1.0, 'Black'),
        ]
        for differential, expected in cases:
            with self.subTest(differential):
                self.assertEqual(
                    bands.get_band(Differential.Reach.ISIS, differential).name,
                    expected,
                )
    
    
    def test__godstow(self):
        """Names the band containing each differential, including the exact boundaries."""
        
        cases = [
            (0.0, 'Low green'),
            (0.215, 'High green'),
            (0.450, 'Green/amber borderline'),
            (0.470, 'Low amber'),
            (0.560, 'Mid amber'),
            (0.640, 'High amber'),
            (0.750, 'Amber/red borderline'),
            (0.770, 'Red'),
            (1.2, 'Red'),
        ]
        for differential, expected in cases:
            with self.subTest(differential):
                self.assertEqual(
                    bands.get_band(Differential.Reach.GODSTOW, differential).name,
                    expected,
                )
    
    
    def test__reach_without_bands(self):
        """Has no band for reaches that are not flagged."""
        
        self.assertIsNone(bands.get_band(Differential.Reach.RADLEY, 0.3))
    
    
    def test__model_property(self):
        """Is available on the differential itself."""
        
        differential = Differential(reach = Differential.Reach.ISIS, differential = 0.3)
        self.assertEqual(differential.band.name, 'Mid blue')
        self.assertEqual(differential.band.styling, 'bg-primary')
    
    
    def test__borderline_styling(self):
        """Stripes borderlines with the colours either side."""
        
        band = bands.get_band(Differential.Reach.GODSTOW, 0.45)
        self.assertEqual(band.styling, 'band-borderline band-green-amber')
    
    
    def test__history_url(self):
        """Links to the reach's page on Jameson's site."""
        
        for reach, slug in [
            (Differential.Reach.ISIS, 'isis'),
            (Differential.Reach.RADLEY, 'radley'),
            (Differential.Reach.WALLINGFORD, 'wallingford'),
        ]:
            with self.subTest(slug):
                self.assertEqual(
                    Differential(reach = reach).history_url,
                    f'https://flags.jamesonlee.com/{slug}',
                )
    
    
    def test__bands_match_automation_boundaries(self):
        """Every flag boundary used for automated flagging sits inside a borderline band."""
        
        from automation import tasks
        
        light_to_blue = 0.330  # Light blue is treated as blue, so this is not a flag change
        reaches = {
            'isis': (Differential.Reach.ISIS, tasks.isis_boundaries),
            'godstow': (Differential.Reach.GODSTOW, tasks.godstow_boundaries),
        }
        for tag, (reach, boundaries) in reaches.items():
            for boundary, _flag in boundaries:
                if boundary == light_to_blue:
                    continue
                with self.subTest(f'{tag} {boundary}'):
                    band = bands.get_band(reach, boundary)
                    self.assertIn('borderline', band.name)
