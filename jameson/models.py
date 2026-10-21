from datetime import timedelta

from django.db import models
from django.utils import timezone


class Differential(models.Model):
    
    class Reach(models.IntegerChoices):
        ISIS = (1, 'The Isis')
        GODSTOW = (2, 'Godstow')
        RADLEY = (3, 'Radley')
        ABINGDON = (4, 'Abingdon')
        WALLINGFORD = (5, 'Wallingford')
    
    TREND_WINDOW = timedelta(hours = 2)
    TREND_THRESHOLD = 0.010  # Metres of change over the window needed to count as moving

    reach = models.IntegerField(choices = Reach.choices)
    time = models.DateTimeField(primary_key = True)
    differential = models.FloatField(db_column = 'flow')
    
    class Meta:
        db_table = 'flag'
        managed = False
        ordering = ['reach', '-time']
    
    
    @property
    def tag(self):
        """The reach's tag, which matches those used in the flags app and on Jameson's site."""
        return self.Reach(self.reach).name.lower()
    
    
    @property
    def out_of_date(self):
        return (timezone.now() - self.time) > timedelta(hours = 4)
    
    
    @property
    def band(self):
        """The band this differential falls in, if its reach has any."""
        
        from . import bands  # Imported here as bands depends on this module
        return bands.get_band(self.reach, self.differential)
    
    
    @property
    def trend(self):
        """Whether the differential rose, fell or held steady over the preceding two hours.

        None if there is no earlier reading in that window to compare against.
        """

        earliest = (
            Differential.objects.using('jameson')
            .filter(
                reach = self.reach,
                time__gte = self.time - self.TREND_WINDOW,
                time__lt = self.time,
            )
            .order_by('time')
            .first()
        )
        if earliest is None:
            return None

        change = self.differential - earliest.differential
        if change >= self.TREND_THRESHOLD:
            return 'rising'
        if change <= -self.TREND_THRESHOLD:
            return 'falling'
        return 'steady'


    @property
    def history_url(self):
        """The page on Jameson's site that shows the history for this reach."""
        
        return f'https://flags.jamesonlee.com/{self.tag}'
    
    
    @classmethod
    def latest_by_reach(cls):
        """The most recent differential for each reach that has one, in reach order."""
        
        latest = (
            cls.objects.using('jameson').filter(reach = reach).first()
            for reach in cls.Reach.values
        )
        return [differential for differential in latest if differential is not None]

