from django.core.management.base import BaseCommand

from ... import models
from ... import data


class Command(BaseCommand):
    help = data.scrape_ourcs_flag_history.__doc__
    
    def handle(self, *args, **kwargs):
        for reach in models.Reach.objects.filter(has_ourcs_flag = True):
            try:
                data.scrape_ourcs_flag_history(reach)
            except Exception:
                continue


