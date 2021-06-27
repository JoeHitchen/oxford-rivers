from datetime import datetime

from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
import pytz

from ... import models


flag_text_map = {
    'Grey': 'X',
    'Green': 'G',
    'Blue': 'B',
    'Amber': 'A',
    'Red': 'R',
    'Black': 'D',
}


class Command(BaseCommand):
    """ **UNTESTED** - This command is not expected to be called regularly."""
    help = 'Retrieves historical flag information from the OURCs website'
    
    def handle(self, *args, **kwargs):
        """Perform lookup for all reaches that have OURCs flags."""
        
        for reach in models.Reach.objects.filter(has_ourcs_flag = True):
            self.fetch_for_reach(reach)
    
    
    @staticmethod
    def fetch_for_reach(reach):
        """Main lookup routine."""
        
        # Request and parse OURCs flag pages
        response = requests.get('https://ourcs.co.uk/information/flags/{}/'.format(reach.tag))
        if not response.ok:
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Retrieve existing status records
        already_recorded = [(status.flag, status.set_at) for status in reach.statuses.all()]
        
        # Iterate over historical statuses
        statuses = []
        previous_status_flag = None
        for status_row in soup.find_all('table')[2].contents[3].find_all('tr')[::-1]:
            
            # Extract status information
            status_row_elements = status_row.find_all('td')
            status_flag = flag_text_map[status_row_elements[0].contents[0]]
            
            status_start_string = status_row_elements[1].contents[0]
            status_start_naive = datetime.strptime(status_start_string, '%d/%m/%y %H:%M')
            status_start_aware = status_start_naive.astimezone(pytz.timezone('Europe/London'))
            
            # De-duplication checks
            if (status_flag, status_start_aware) in already_recorded:
                previous_status_flag = status_flag
                continue
            if status_flag == previous_status_flag:
                continue
            previous_status_flag = status_flag
            
            # Create status record
            statuses.append(models.Status(
                reach = reach,
                flag = status_flag,
                set_at = status_start_aware,
            ))
        
        # Store all statuses
        models.Status.objects.bulk_create(statuses)

