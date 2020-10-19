from django.db import models


class Reach(models.Model):
    name = models.CharField(max_length = 12)
    tag = models.SlugField(max_length = 12, unique = True)  # Implicit db index


class Advisory(models.Model):
    
    class Boards(models.TextChoices):
        NONE = ('NONE', 'No advisory')
        INC = ('INC', 'Caution (Increasing)')
        DEC = ('DEC', 'Caution (Decreasing)')
        RED = ('RED', 'Danger')
    
    reach = models.ForeignKey(Reach, models.CASCADE, related_name = 'advisories')
    board = models.CharField(max_length = 4, choices = Boards.choices)
    active_from = models.DateTimeField(default=timezone.now)
    active_until = models.DateTimeField(null = True)
    
    def __str__(self):
        return self.get_board_display()

