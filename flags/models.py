from django.db import models, transaction
from django.utils import timezone


class Reach(models.Model):
    name = models.CharField(max_length = 12)
    tag = models.SlugField(max_length = 12, unique = True)  # Implicit db index
    downstream_order = models.PositiveSmallIntegerField()
    
    class Meta:
        ordering = ['downstream_order']
    
    def __str__(self):
        return self.name
    
    @property
    def current_advisory(self):
        return self.advisories.filter(first_updated__lte = timezone.now()).first()
    
    
    def update_advisory(self, new_board, board_shown = timezone.now()):
        """Updates advisory records to reflect `new_board` being displayed at `board_shown`."""
        
        # Update existing matching advisory
        if self.current_advisory and self.current_advisory.board == new_board:
            advisory = self.current_advisory
            advisory.last_updated = board_shown
            advisory.last_seen = timezone.now()
            advisory.save()
        
        # Create new advisory if mismatched or missing
        else:
            self.advisories.create(
                board = new_board,
                first_updated = board_shown,
                last_updated = board_shown,
            )


class Advisory(models.Model):
    
    class Boards(models.TextChoices):
        NONE = ('NONE', 'No advisory')
        INC = ('INC', 'Caution (Increasing)')
        DEC = ('DEC', 'Caution (Decreasing)')
        RED = ('RED', 'Danger')
    
    reach = models.ForeignKey(Reach, models.CASCADE, related_name = 'advisories')
    board = models.CharField(max_length = 4, choices = Boards.choices)
    
    first_seen = models.DateTimeField(default=timezone.now)     # When board first seen (by our retrievals)
    first_updated = models.DateTimeField(default=timezone.now)  # When board first displayed (according to EA)
    last_seen = models.DateTimeField(default=timezone.now)      # When board last seen (by our retrievals)
    last_updated = models.DateTimeField(default=timezone.now)   # When board last affirmed (according to EA)
    
    class Meta:
        ordering = ['reach', '-first_updated']
    
    def __str__(self):
        return self.get_board_display()
    
    def styling(self):
        return {
            self.Boards.NONE: {'text': 'text-dark', 'background': 'bg-light'},
            self.Boards.INC: {'text': 'text-dark', 'background': 'bg-warning'},
            self.Boards.DEC: {'text': 'text-dark', 'background': 'bg-warning'},
            self.Boards.RED: {'text': 'text-light', 'background': 'bg-danger'},
        }[self.board]

