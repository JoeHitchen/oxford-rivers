from datetime import timedelta

from django.db import models
from django.utils import timezone


class Differential(models.Model):
    
    class Reach(models.IntegerChoices):
        ISIS = (1, 'Isis')
        GODSTOW = (2, 'Godstow')
        RADLEY = (3, 'Radley')
        ABINGDON = (4, 'Abingdon')
        WALLINGFORD = (5, 'Wallingford')
    
    reach = models.IntegerField(choices = Reach.choices)
    time = models.DateTimeField(primary_key = True)
    differential = models.FloatField(db_column = 'flow')
    
    class Meta:
        db_table = 'flag'
        managed = False
        ordering = ['reach', '-time']
    
    
    @property
    def tag(self):
        """The reach's name in lower case, which matches the tags used in the flags app."""
        return self.get_reach_display().lower()
    
    
    @property
    def out_of_date(self):
        return (timezone.now() - self.time) > timedelta(hours = 4)
    
    
    @property
    def band(self):
        """The band this differential falls in, if its reach has any."""
        
        from . import bands  # Imported here as bands depends on this module
        return bands.get_band(self.reach, self.differential)
    
    
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

