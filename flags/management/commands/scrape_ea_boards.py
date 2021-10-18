from django.core.management.base import BaseCommand

from ... import data


class Command(BaseCommand):
    help = data.scrape_ea_boards.__doc__
    
    def handle(self, *args, **kwargs):
        data.scrape_ea_boards()


