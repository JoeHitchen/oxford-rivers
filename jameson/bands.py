from collections import namedtuple

from . import models


Band = namedtuple('Band', ['lower_bound', 'name', 'styling'])
# ^ The styling is a space-separated list of CSS classes for displaying the band

GREEN = 'bg-success'
BLUE = 'bg-primary'
AMBER = 'bg-warning'
RED = 'bg-danger text-light'
BLACK = 'bg-dark text-light'


def borderline(lower, upper):
    """Styling for a borderline, which is striped with the colours of the flags either side."""
    return f'band-borderline band-{lower}-{upper}'


BANDS = {
    models.Differential.Reach.ISIS: [
        Band(None, 'Low Green', GREEN),
        Band(0.100, 'High Green', GREEN),
        Band(0.195, 'Green/Blue Borderline', borderline('green', 'blue')),
        Band(0.235, 'Low Blue', BLUE),
        Band(0.297, 'Mid Blue', BLUE),
        Band(0.360, 'High Blue', BLUE),
        Band(0.422, 'Blue/Amber Borderline', borderline('blue', 'amber')),
        Band(0.462, 'Amber', AMBER),
        Band(0.515, 'Amber/Red Borderline', borderline('amber', 'red')),
        Band(0.555, 'Low Red', RED),
        Band(0.628, 'High Red', RED),
        Band(0.720, 'Black', BLACK),
    ],
    models.Differential.Reach.GODSTOW: [
        Band(None, 'Low Green', GREEN),
        Band(0.215, 'High Green', GREEN),
        Band(0.430, 'Green/Amber Borderline', borderline('green', 'amber')),
        Band(0.470, 'Low Amber', AMBER),
        Band(0.560, 'Mid Amber', AMBER),
        Band(0.640, 'High Amber', AMBER),
        Band(0.730, 'Amber/Red Borderline', borderline('amber', 'red')),
        Band(0.770, 'Red', RED),
    ],
}


def get_band(reach, differential):
    """The band containing a differential, or None if the reach has no bands."""
    
    containing_band = None
    for band in BANDS.get(reach, []):
        if band.lower_bound is not None and differential < band.lower_bound:
            break
        containing_band = band
    return containing_band
