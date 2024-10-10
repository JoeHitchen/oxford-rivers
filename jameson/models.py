from django.db import models


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

