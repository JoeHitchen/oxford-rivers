from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from . import bands
from .models import Differential


class Test_Bands(SimpleTestCase):
    
    def test__isis(self):
        """Names the band containing each differential, either side of each boundary."""
        
        cases = [
            (-0.100, 'Low Green'),
            (0.099, 'Low Green'), (0.100, 'High Green'), (0.101, 'High Green'),
            (0.194, 'High Green'), (0.195, 'Green/Blue Borderline'),
            (0.196, 'Green/Blue Borderline'),
            (0.234, 'Green/Blue Borderline'), (0.235, 'Low Blue'), (0.236, 'Low Blue'),
            (0.296, 'Low Blue'), (0.297, 'Mid Blue'), (0.298, 'Mid Blue'),
            (0.359, 'Mid Blue'), (0.360, 'High Blue'), (0.361, 'High Blue'),
            (0.421, 'High Blue'), (0.422, 'Blue/Amber Borderline'),
            (0.423, 'Blue/Amber Borderline'),
            (0.461, 'Blue/Amber Borderline'), (0.462, 'Amber'), (0.463, 'Amber'),
            (0.514, 'Amber'), (0.515, 'Amber/Red Borderline'),
            (0.516, 'Amber/Red Borderline'),
            (0.554, 'Amber/Red Borderline'), (0.555, 'Low Red'), (0.556, 'Low Red'),
            (0.627, 'Low Red'), (0.628, 'High Red'), (0.629, 'High Red'),
            (0.719, 'High Red'), (0.720, 'Black'), (0.721, 'Black'),
            (1.000, 'Black'),
        ]
        for differential, expected in cases:
            with self.subTest(differential):
                self.assertEqual(
                    bands.get_band(Differential.Reach.ISIS, differential).name,
                    expected,
                )
    
    
    def test__godstow(self):
        """Names the band containing each differential, either side of each boundary."""
        
        cases = [
            (0.000, 'Low Green'),
            (0.214, 'Low Green'), (0.215, 'High Green'), (0.216, 'High Green'),
            (0.429, 'High Green'), (0.430, 'Green/Amber Borderline'),
            (0.431, 'Green/Amber Borderline'),
            (0.469, 'Green/Amber Borderline'), (0.470, 'Low Amber'), (0.471, 'Low Amber'),
            (0.559, 'Low Amber'), (0.560, 'Mid Amber'), (0.561, 'Mid Amber'),
            (0.639, 'Mid Amber'), (0.640, 'High Amber'), (0.641, 'High Amber'),
            (0.729, 'High Amber'), (0.730, 'Amber/Red Borderline'),
            (0.731, 'Amber/Red Borderline'),
            (0.769, 'Amber/Red Borderline'), (0.770, 'Red'), (0.771, 'Red'),
            (1.200, 'Red'),
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
        self.assertEqual(differential.band.name, 'Mid Blue')
        self.assertEqual(differential.band.styling, 'bg-primary')
    
    
    def test__borderline_styling(self):
        """Stripes borderlines with the colours either side."""
        
        band = bands.get_band(Differential.Reach.GODSTOW, 0.45)
        self.assertEqual(band.styling, 'band-borderline band-green-amber')
    
    
    def test__tag(self):
        """Matches the flags app tags, and not the display name."""
        
        differential = Differential(reach = Differential.Reach.ISIS)
        self.assertEqual(differential.get_reach_display(), 'The Isis')
        self.assertEqual(differential.tag, 'isis')
    
    
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
        """Every flag boundary used for automated flagging sits inside a borderline band.
        
        The exception is black, which starts exactly at its boundary.
        """
        
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
                    self.assertTrue('Borderline' in band.name or band.lower_bound == boundary)
    
    
    def test__out_of_date(self):
        """Is out of date when more than four hours old."""
        
        for age, expected in [
            (timedelta(hours = 3, minutes = 59), False),
            (timedelta(hours = 4, minutes = 1), True),
        ]:
            with self.subTest(age):
                differential = Differential(
                    reach = Differential.Reach.ISIS,
                    time = timezone.now() - age,
                )
                self.assertEqual(differential.out_of_date, expected)
