"""Named bands of differential, used to describe what a differential value means for a reach.

Each band runs from its lower bound (inclusive) to the lower bound of the next band. The
borderline bands are +/- 0.02 either side of the boundary between two flags, as set out for
automated flagging in `automation.tasks`. Light blue is not treated as a distinct flag.
"""

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
        Band(None, 'Low green', GREEN),
        Band(0.100, 'High green', GREEN),
        Band(0.195, 'Green/blue borderline', borderline('green', 'blue')),
        Band(0.235, 'Low blue', BLUE),
        Band(0.297, 'Mid blue', BLUE),
        Band(0.360, 'High blue', BLUE),
        Band(0.422, 'Blue/amber borderline', borderline('blue', 'amber')),
        Band(0.462, 'Amber', AMBER),
        Band(0.515, 'Amber/red borderline', borderline('amber', 'red')),
        Band(0.555, 'Low red', RED),
        Band(0.628, 'High red', RED),
        Band(0.700, 'Red/black borderline', borderline('red', 'black')),
        Band(0.740, 'Black', BLACK),
    ],
    models.Differential.Reach.GODSTOW: [
        Band(None, 'Low green', GREEN),
        Band(0.215, 'High green', GREEN),
        Band(0.430, 'Green/amber borderline', borderline('green', 'amber')),
        Band(0.470, 'Low amber', AMBER),
        Band(0.560, 'Mid amber', AMBER),
        Band(0.640, 'High amber', AMBER),
        Band(0.730, 'Amber/red borderline', borderline('amber', 'red')),
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
