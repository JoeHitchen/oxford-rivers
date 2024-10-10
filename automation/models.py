from django.db import models

from flags import models as flags


class AutoFlag(flags.Reach):
    
    enabled = models.BooleanField(default = True)
    status = models.CharField(max_length = 1, choices = flags.Status.Flags.choices)

