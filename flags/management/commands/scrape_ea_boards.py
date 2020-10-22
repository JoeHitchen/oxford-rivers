from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from bs4 import BeautifulSoup

from ... import models


downstream_lock_map = {
    'isis': 'Iffley Lock',
    'godstow': 'Osney Lock',
    'radley': 'Abingdon Lock',
    'abingdon': 'Culham Lock',
    'wallingford': 'Cleeve Lock',
    'sandford': 'Sandford Lock',
}


board_text_map = {
    'no stream warnings': models.Advisory.Boards.NONE,
    'caution stream increasing': models.Advisory.Boards.INC,
    'caution stream decreasing': models.Advisory.Boards.DEC,
    'caution strong stream': models.Advisory.Boards.RED,
}


class Command(BaseCommand):
    help = 'Retrieves stream advisory boards from the EA website'
    
    def handle(self, *args, **kwargs):
        
        response = requests.get('http://riverconditions.environment-agency.gov.uk/')
        if not response.ok:
            print('Error fetching EA boards page')
        
        soup = BeautifulSoup(response.text, 'html.parser')
        main_column = soup.find(class_ = 'primary-column')
        
        reaches = models.Reach.objects.all()
        for reach in reaches:
            board = extract_board(main_column, downstream_lock_map[reach.tag])
            reach.update_advisory(board)


def extract_board(main_column, downstream_lock):
    
    reach_row = main_column.find(text = downstream_lock).parent.parent.parent
    board_outer = reach_row.contents[1].contents[0]
    board_inner = board_outer.contents[0].contents[0].contents[0].contents[0]
    
    return board_text_map[board_inner.lower()]

