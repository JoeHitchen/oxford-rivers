from django.core.management.base import BaseCommand

from ... import data


class Command(BaseCommand):
    help = data.fetch_thames_water_discharges.__doc__
    
    def handle(self, *args, **kwargs):
        data.fetch_thames_water_discharges()
