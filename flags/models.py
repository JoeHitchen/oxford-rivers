from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


class Reach(models.Model):
    """Describes a stretch of river."""
    
    name = models.CharField(max_length = 12)
    tag = models.SlugField(max_length = 12, unique = True)  # Implicit db index
    downstream_order = models.PositiveSmallIntegerField()
    
    class Meta:
        ordering = ['downstream_order']
    
    def __str__(self):
        return self.name
    
    
    @property
    def upstream_lock(self):
        return {
            'isis': 'Osney',
            'godstow': 'Godstow',
            'radley': 'Sandford',
            'abingdon': 'Abingdon',
            'wallingford': 'Benson',
            'sandford': 'Iffley',
        }[self.tag]
    
    
    @property
    def downstream_lock(self):
        return {
            'isis': 'Iffley',
            'godstow': 'Osney',
            'radley': 'Abingdon',
            'abingdon': 'Culham',
            'wallingford': 'Cleeve',
            'sandford': 'Sandford',
        }[self.tag]
    
    
    @cached_property
    def current_advisory(self):
        """The most recently shown EA stream advisory for the reach."""
        return self.advisories.filter(first_updated__lte = timezone.now()).first()
    
    
    def update_advisory(self, new_board, board_shown = timezone.now()):
        """Updates EA advisory records to reflect `new_board` being displayed at `board_shown`."""
        
        # Update existing matching advisory
        if self.current_advisory and self.current_advisory.board == new_board:
            self.current_advisory.last_updated = board_shown
            self.current_advisory.last_seen = timezone.now()
            self.current_advisory.save()
        
        # Create new advisory if mismatched or missing
        else:
            self.advisories.create(
                board = new_board,
                first_updated = board_shown,
                last_updated = board_shown,
            )
        
        # Reset current advisory cache
        del self.current_advisory


class Advisory(models.Model):
    """A private model describing EA stream advisories for use through the Reach model.
    
    first_seen - When board first seen (by our retrievals)
    first_updated - When board first displayed (according to EA)
    last_seen - When board last seen (by our retrievals)
    last_updated - When board last affirmed (according to EA)
    """
    
    class Boards(models.TextChoices):
        NONE = ('NONE', 'No advisory')
        INC = ('INC', 'Caution (Increasing)')
        DEC = ('DEC', 'Caution (Decreasing)')
        RED = ('RED', 'Danger')
    
    reach = models.ForeignKey(Reach, models.CASCADE, related_name = 'advisories')
    board = models.CharField(max_length = 4, choices = Boards.choices)
    
    first_seen = models.DateTimeField(default=timezone.now)
    first_updated = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['reach', '-first_updated']
    
    def __str__(self):
        return self.get_board_display()
    
    def styling(self):
        return {
            self.Boards.NONE: {'text': 'text-dark', 'background': 'bg-none'},
            self.Boards.INC: {'text': 'text-dark', 'background': 'bg-warning'},
            self.Boards.DEC: {'text': 'text-dark', 'background': 'bg-warning'},
            self.Boards.RED: {'text': 'text-light', 'background': 'bg-danger'},
        }[self.board]

