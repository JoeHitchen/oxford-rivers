from django.db import models
from django.utils import timezone


class Station(models.Model):
    """A Thames Water storm discharge monitoring station.

    river - The major river that the station ultimately feeds in to
    watercourse - The minor river/watercourse that the station directly feeds in to
    name - The station's name, typically the specific location of the station
    permit_number - The station's unique discharge permit number
    last_reading_at - When the station's discharge status was last successfully read
    """

    class Rivers(models.TextChoices):
        THAMES = ('thames', 'Thames')
        CHERWELL = ('cherwell', 'Cherwell')
        SEACOURT = ('seacourt', 'Seacourt Stream')

    river = models.CharField(max_length = 10, choices = Rivers.choices)
    watercourse = models.CharField(max_length = 100)
    name = models.CharField(max_length = 100)
    permit_number = models.CharField(max_length = 20, unique = True)

    last_reading_at = models.DateTimeField(null = True, blank = True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DischargeEvent(models.Model):
    """A period of discharge at a station.

    start_at - When the discharge started (according to Thames Water)
    start_seen - When the discharge was first seen (by our retrievals)
    end_at - When the discharge ended (according to Thames Water), if it has
    end_seen - When the end of the discharge was first seen (by our retrievals)
    """

    station = models.ForeignKey(Station, models.CASCADE, related_name = 'events')
    start_at = models.DateTimeField()
    start_seen = models.DateTimeField(default = timezone.now)
    end_at = models.DateTimeField(null = True, blank = True)
    end_seen = models.DateTimeField(null = True, blank = True)

    class Meta:
        ordering = ['-start_at']

    def __str__(self):
        return '{} - {}'.format(self.station, timezone.localtime(self.start_at))

