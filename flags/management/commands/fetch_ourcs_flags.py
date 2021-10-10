from django.core.management.base import BaseCommand

from ... import models
from ... import data


class Command(BaseCommand):
    help = data.fetch_ourcs_flag.__doc__
    
    def handle(self, *args, **kwargs):
        for reach in models.Reach.objects.filter(has_ourcs_flag = True):
            try:
                data.fetch_ourcs_flag(reach)
            except Exception:
                continue


