from datetime import datetime
from random import randrange
from time import sleep
import logging

from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
import pytz

from ... import models

logger = logging.getLogger('EA Boards')
logger.setLevel('INFO')


board_text_map = {
    'no stream warnings': models.Advisory.Boards.NONE,
    'caution stream increasing': models.Advisory.Boards.INC,
    'caution stream decreasing': models.Advisory.Boards.DEC,
    'caution strong stream': models.Advisory.Boards.RED,
}


class Command(BaseCommand):
    help = 'Retrieves stream advisory boards from the EA website'
    
    def add_arguments(self, parser):
        """Defines the optional arguments to the command."""
        parser.add_argument(
            '--delay',
            action = 'store_true',
            help = 'Delay collection by between 60 and 180 seconds',
        )
    
    
    def handle(self, *args, **kwargs):
        """Main execution routine."""
        
        # Optionally delay data collection (to be a good netizen)
        if kwargs.get('delay', False):
            delay = randrange(60, 180)
            logger.info('Delaying collection for {} seconds'.format(delay))
            sleep(delay)
        logger.info('Running data collection')
        
        # Request and parse EA Boards page
        response = requests.get('http://riverconditions.environment-agency.gov.uk/')
        if not response.ok:
            logger.error('Error fetching EA boards page')
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract last-updated datetime
        last_updated_element = soup.find(class_ = 'last-update')
        last_updated_string = last_updated_element.contents[0].split(': ')[1]
        last_updated = datetime.strptime(last_updated_string, '%d %B %Y %H:%M')
        last_updated = last_updated.astimezone(pytz.timezone('Europe/London'))
        logger.info('Boards updated {}'.format(last_updated))
        
        # Extract boards
        main_column = soup.find(class_ = 'primary-column')
        for reach in models.Reach.objects.all():
            board = self.extract_board(main_column, reach.downstream_lock)
            logger.info('{:11s} {}'.format(str(reach), models.Advisory.Boards(board).label))
            
            models.Reach.update_advisory(reach, board, board_shown = last_updated)
            # ^ Class method used for testing purposes
        
        logger.info('Collection completed')
    
    
    @staticmethod
    def extract_board(main_column, downstream_lock):
        """Extracts the board for a reach above a specific lock."""
        
        reach_row = main_column.find(text = downstream_lock + ' Lock').parent.parent.parent
        board_outer = reach_row.contents[1].contents[0]
        board_inner = board_outer.contents[0].contents[0].contents[0].contents[0]
        
        return board_text_map[board_inner.lower()]

