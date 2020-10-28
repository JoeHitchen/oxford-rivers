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
        return self.advisories.filter(Advisory.Q_filter_active()).first()
    
    
    def update_advisory(self, new_board, board_shown = timezone.now()):
        
        if self.current_advisory and self.current_advisory.board == new_board:
            return
        
        with transaction.atomic():
            self.advisories.create(board = new_board, first_updated = board_shown)


class Advisory(models.Model):
    
    class Boards(models.TextChoices):
        NONE = ('NONE', 'No advisory')
        INC = ('INC', 'Caution (Increasing)')
        DEC = ('DEC', 'Caution (Decreasing)')
        RED = ('RED', 'Danger')
    
    reach = models.ForeignKey(Reach, models.CASCADE, related_name = 'advisories')
    board = models.CharField(max_length = 4, choices = Boards.choices)
    
    first_updated = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['reach', '-first_updated']
    
    def __str__(self):
        return self.get_board_display()
    
    @staticmethod
    def Q_filter_active():
        return models.Q(
            models.Q(first_updated__lte = timezone.now())
        )
    
    def styling(self):
        return {
            self.Boards.NONE: {'text': 'text-dark', 'background': 'bg-light'},
            self.Boards.INC: {'text': 'text-dark', 'background': 'bg-warning'},
            self.Boards.DEC: {'text': 'text-dark', 'background': 'bg-warning'},
            self.Boards.RED: {'text': 'text-light', 'background': 'bg-danger'},
        }[self.board]

