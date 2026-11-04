from datetime import timedelta

from django.db import models
from django.utils import timezone

RECENT_WINDOW = timedelta(hours = 48)
OUT_OF_DATE_AFTER = timedelta(hours = 2)


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
    
    def update_discharge_status(self, new_status = None, status_changed = None):
        """Updates the records to reflect the latest status reported for the station."""

        active_discharge = self.events.filter(end_at__isnull = True).first()

        # Handle offline stations
        if new_status in (None, 'Offline'):

            # Close off expired discharges for offline stations
            if active_discharge and self.last_reading_at < timezone.now() - RECENT_WINDOW:
                active_discharge.end_at = self.last_reading_at
                active_discharge.end_seen = self.last_reading_at
                active_discharge.save()

            return

        # New discharge has started
        if not active_discharge and new_status == 'Discharging':
            self.events.create(start_at = status_changed)

        # Old discharge has ended
        elif active_discharge and new_status == 'Not discharging':
            active_discharge.end_at = status_changed
            active_discharge.end_seen = timezone.now()
            active_discharge.save()

        self.last_reading_at = timezone.now()
        self.save()


    @classmethod
    def summary(cls):
        """The headline numbers across all monitored stations.

        A station is actively discharging if it has an ongoing discharge, and has discharged
        recently if it has an ongoing discharge or one that ended within the recent window.

        A station is offline if it has had no reading in the last two hours and no discharge
        within the recent window.
        """

        online = (
            models.Q(last_reading_at__gte = timezone.now() - OUT_OF_DATE_AFTER)
            | models.Q(has_recent_discharge = True)
        )
        counts = cls.objects.annotate(
            has_active_discharge = models.Exists(
                DischargeEvent.objects.filter(
                    station = models.OuterRef('pk'),
                    end_at__isnull = True,
                ),
            ),
            has_recent_discharge = models.Exists(
                DischargeEvent.objects.filter(
                    models.Q(end_at__isnull = True)
                    | models.Q(end_at__gte = timezone.now() - RECENT_WINDOW),
                    station = models.OuterRef('pk'),
                ),
            ),
        ).aggregate(
            total = models.Count('pk'),
            online = models.Count('pk', filter = online),
            offline = models.Count('pk', filter = ~online),
            actively_discharging = models.Count(
                'pk', filter = models.Q(has_active_discharge = True),
            ),
            discharged_recently = models.Count(
                'pk', filter = models.Q(has_recent_discharge = True),
            ),
        )

        latest_reading = cls.objects.aggregate(newest = models.Max('last_reading_at'))['newest']

        return {
            'stations_total': counts['total'],
            'stations_offline': counts['offline'],
            'percentage_offline': round(100 * counts['offline'] / (counts['total'] or 1)),
            'stations_online': counts['online'],
            'stations_actively_discharging': counts['actively_discharging'],
            'percentage_actively_discharging': round(
                100 * counts['actively_discharging'] / (counts['online'] or 1),
            ),
            'stations_discharged_recently': counts['discharged_recently'],
            'percentage_discharged_recently': round(
                100 * counts['discharged_recently'] / (counts['online'] or 1),
            ),
            'recent_window_hours': int(RECENT_WINDOW.total_seconds() // 3600),
            'readings_out_of_date': (
                latest_reading is None
                or latest_reading < timezone.now() - OUT_OF_DATE_AFTER
            ),
        }


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


    @property
    def is_active(self):
        return self.end_at is None


    @property
    def is_recent(self):
        return self.is_active or self.end_at >= timezone.now() - RECENT_WINDOW


    def styling(self):
        if self.is_active:
            return 'table-danger'
        if self.is_recent:
            return 'table-warning'
        return ''


    @property
    def latest_update_seen(self):
        """The most recent confirmation of the discharge event being active or having ended."""
        return self.end_seen or self.station.last_reading_at


    @classmethod
    def recent_discharges(cls):
        """Active events, then those that ended within the recent window, newest first."""
        return cls.objects.filter(
            models.Q(end_at__isnull = True)
            | models.Q(end_at__gte = timezone.now() - RECENT_WINDOW),
        ).select_related('station').order_by(
            models.F('end_at').desc(nulls_first = True),
            '-start_at',
        )
