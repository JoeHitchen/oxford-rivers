from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


class Reach(models.Model):
    """Describes a stretch of river."""
    
    class Common(models.TextChoices):
        ISIS = 'isis'
        GODS = 'godstow'
        RAD = 'radley'
        AB = 'abingdon'
        WALLI = 'wallingford'
        SAND = 'sandford'
    
    name = models.CharField(max_length = 12)
    tag = models.SlugField(max_length = 12, unique = True)  # Implicit db index
    downstream_order = models.PositiveSmallIntegerField()
    has_ourcs_flag = models.BooleanField(default = False)
    
    class Meta:
        ordering = ['downstream_order']
    
    def __str__(self):
        return self.name
    
    
    @property
    def upstream_lock(self):
        return {
            self.Common.ISIS: 'Osney',
            self.Common.GODS: 'Godstow',
            self.Common.RAD: 'Sandford',
            self.Common.AB: 'Abingdon',
            self.Common.WALLI: 'Benson',
            self.Common.SAND: 'Iffley',
        }[self.tag]
    
    
    @property
    def downstream_lock(self):
        return {
            self.Common.ISIS: 'Iffley',
            self.Common.GODS: 'Osney',
            self.Common.RAD: 'Abingdon',
            self.Common.AB: 'Culham',
            self.Common.WALLI: 'Cleeve',
            self.Common.SAND: 'Sandford',
        }[self.tag]
    
    
    @cached_property
    def current_flag_status(self):
        """The most recently shown OURCs flag for the reach."""
        return self.statuses.all().first()
    
    
    @cached_property
    def current_advisory(self):
        """The most recently shown EA stream advisory for the reach.
        
        N.B. Filtering by current time leads to issue #1.
        """
        return self.advisories.all().first()
    
    
    def update_flag_status(self, new_flag, set_at, set_by = ''):
        """Updates the OURCs flag status to reflect the latest observation."""
        
        # Update existing matching flag
        if self.current_flag_status and self.current_flag_status.flag == new_flag:
            
            if not self.current_flag_status.set_by:
                self.current_flag_status.set_by = set_by
            
            self.current_flag_status.last_seen = timezone.now()
            self.current_flag_status.save()
        
        # Create new status if mismatched or missing
        else:
            self.statuses.create(
                flag = new_flag,
                set_at = set_at,
                set_by = set_by,
            )
        
        # Reset current flag cache
        del self.current_flag_status
    
    
    def update_advisory(self, new_board, board_shown = timezone.now()):
        """Updates EA advisory records to reflect `new_board` being displayed at `board_shown`."""
        
        # Short outages are ignored at first
        if (
            new_board == Advisory.Boards.OUT
            and not self.current_advisory.board == Advisory.Boards.OUT
            and self.current_advisory.last_seen >= timezone.now() - timedelta(hours = 24)
        ):
            return
        
        # Update existing matching advisory if no significant gap
        if (
            self.current_advisory and self.current_advisory.board == new_board
            and self.current_advisory.last_seen >= timezone.now() - timedelta(hours = 24)
        ):
            self.current_advisory.last_updated = board_shown
            self.current_advisory.last_seen = timezone.now()
            self.current_advisory.save()
        
        # Mismatched or missing advisory
        else:
        
            # Create additional outage report if significant time gap
            if (
                self.current_advisory and new_board != Advisory.Boards.OUT
                and self.current_advisory.last_seen <= timezone.now() - timedelta(hours = 4)
            ):
                self.advisories.create(
                    board = Advisory.Boards.OUT,
                    first_seen = self.current_advisory.last_seen + timedelta(hours = 1),
                    first_updated = self.current_advisory.last_updated + timedelta(hours = 1),
                    last_seen = timezone.now() - timedelta(hours = 1),
                    last_updated = board_shown - timedelta(hours = 1),
                )
            
            # Create new advisory
            self.advisories.create(
                board = new_board,
                first_updated = board_shown,
                last_updated = board_shown,
            )
        
        # Reset current advisory cache
        del self.current_advisory


class Status(models.Model):
    """Describes the raising of an OURCs flag."""
    
    class Flags(models.TextChoices):
        GREY = ('X', 'Grey')
        GREEN = ('G', 'Green')
        LIGHT = ('L', 'Light Blue')
        BLUE = ('B', 'Blue')
        AMBER = ('A', 'Amber')
        RED = ('R', 'Red')
        BLACK = ('D', 'Black')
    
    reach = models.ForeignKey(Reach, models.CASCADE, related_name = 'statuses')
    flag = models.CharField(max_length = 1, choices = Flags.choices)
    set_at = models.DateTimeField()
    set_by = models.CharField(max_length = 50, blank = True)
    
    first_seen = models.DateTimeField(default = timezone.now)
    last_seen = models.DateTimeField(default = timezone.now)
    
    class Meta:
        ordering = ['reach', '-set_at']
    
    def __str__(self):
        return self.get_flag_display()
    
    @property
    def out_of_date(self):
        return (timezone.now() - self.last_seen) > timedelta(hours = 2)
    
    def styling(self):
        return {
            self.Flags.GREY: 'bg-secondary',
            self.Flags.GREEN: 'bg-success',
            self.Flags.LIGHT: 'bg-lightblue',
            self.Flags.BLUE: 'bg-primary',
            self.Flags.AMBER: 'bg-warning',
            self.Flags.RED: 'bg-danger text-light',
            self.Flags.BLACK: 'bg-dark text-light',
        }.get(self.flag)


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
        OUT = ('OUT', 'Outage')
    
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
    
    @property
    def out_of_date(self):
        return (timezone.now() - self.last_seen) > timedelta(hours = 2)
    
    def styling(self):
        return {
            self.Boards.NONE: 'bg-none',
            self.Boards.INC: 'bg-warning',
            self.Boards.DEC: 'bg-warning',
            self.Boards.RED: 'bg-danger',
            self.Boards.OUT: 'bg-secondary text-white',
        }[self.board]

