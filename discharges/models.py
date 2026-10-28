from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

RECENT_WINDOW = timedelta(hours = 48)
OUT_OF_DATE_AFTER = timedelta(hours = 2)


class Station(models.Model):
    """A Thames Water storm discharge monitor.

    last_reading_at - When the monitor last gave a real reading, i.e. it reported that it was
        discharging or not discharging. Monitors that are offline do not advance this.
    """

    class Rivers(models.TextChoices):
        THAMES = ('thames', 'Thames')
        CHERWELL = ('cherwell', 'Cherwell')
        SEACOURT = ('seacourt', 'Seacourt Stream')

    permit_number = models.CharField(max_length = 20, unique = True)
    name = models.CharField(max_length = 100)
    watercourse = models.CharField(max_length = 100)
    river = models.CharField(max_length = 10, choices = Rivers.choices)
    last_reading_at = models.DateTimeField(null = True, blank = True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


    @cached_property
    def open_event(self):
        """The event for the discharge that is currently in progress, if any."""
        return self.events.active().first()
    
    
    def record_discharging(self, status_changed):
        """Updates the records to reflect the monitor reporting an ongoing discharge."""
        
        if not self.open_event:
            self.events.create(start_at = status_changed)
        
        self.last_reading_at = timezone.now()
        self.save(update_fields = ['last_reading_at'])
        self.__dict__.pop('open_event', None)
    
    
    def record_not_discharging(self, status_changed):
        """Updates the records to reflect the monitor reporting no discharge."""
        
        if self.open_event:
            self.open_event.end_at = max(status_changed, self.open_event.start_at)
            self.open_event.end_seen = timezone.now()
            self.open_event.save()
        
        self.last_reading_at = timezone.now()
        self.save(update_fields = ['last_reading_at'])
        self.__dict__.pop('open_event', None)
    
    
    @classmethod
    def readings_out_of_date(cls):
        """Whether no monitor has given a real reading recently.

        Based on the newest reading rather than the oldest, since individual monitors can remain
        offline for days. If the poller or API fails every monitor stops advancing, so this still
        becomes true.
        """
        newest = cls.objects.aggregate(newest = models.Max('last_reading_at'))['newest']
        return newest is None or (timezone.now() - newest) > OUT_OF_DATE_AFTER


class DischargeEventQuerySet(models.QuerySet):

    def active(self):
        return self.filter(end_at__isnull = True)

    def recent(self):
        """Events that are active or ended within the recent window."""
        return self.filter(
            models.Q(end_at__isnull = True)
            | models.Q(end_at__gte = timezone.now() - RECENT_WINDOW),
        )

    def recent_listing(self):
        """Recent events, with their stations, active first: as shown on the index page."""
        return self.recent().select_related('station').active_first()
    
    def active_first(self):
        """Orders active events before ended ones, then newest first."""
        return self.order_by(models.F('end_at').asc(nulls_first = True), '-start_at')


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

    objects = DischargeEventQuerySet.as_manager()

    class Meta:
        ordering = ['-start_at']

    def __str__(self):
        return '{} - {}'.format(self.station, timezone.localtime(self.start_at))


    @property
    def is_active(self):
        return self.end_at is None


    @property
    def duration(self):
        return (self.end_at or timezone.now()) - self.start_at


    @property
    def latest_update_seen(self):
        """When our latest information about the event is from.

        For an active event this is the last real reading from the station, which must have been
        a discharging reading as a non-discharging one would have ended the event. It stays frozen
        if the monitor goes offline or retrievals fail. For an ended event it is when we saw the
        end.
        """
        return self.end_seen or self.station.last_reading_at
