import logging

from django.core.management.base import BaseCommand
import requests

from ... import models

logger = logging.getLogger('OURCs Flags')
logger.setLevel('INFO')


class Command(BaseCommand):
    help = 'Retrieves current flag information from the OURCs APIs'
    
    def handle(self, *args, **kwargs):
        """Perform retrieval for both Isis and Godstow."""
        
        self.fetch_for_reach(models.Reach.objects.get(tag = 'isis'))
        self.fetch_for_reach(models.Reach.objects.get(tag = 'godstow'))
    
    
    @staticmethod
    def fetch_for_reach(reach):
        """Main lookup routine."""
        logger.info('{} - Fetching...'.format(reach.name))
        
        # Request and parse OURCs flag APIs
        response = requests.get('https://ourcs.co.uk/api/flags/status/{}/'.format(reach.tag))
        if not response.ok:
            response.raise_for_status()
        response_json = response.json()
        
        # Flag changed
        current_status = reach.current_flag_status
        if not current_status or response_json['status'] != current_status.flag:
            logger.info('{} - Changed from {} to {}'.format(
                reach.name,
                current_status and current_status.flag,
                response_json['status'],
            ))
            
            # Create new status
            reach.statuses.create(
                flag = response_json['status'],
                set_at = response_json['set_date'],
                set_by = response_json.get('set_by', ''),
            )
        
        # Flag unchanged
        else:
            logger.info('{} - Unchanged at {}'.format(reach.name, current_status.flag))
            
            # Add missing set-by
            set_by = response_json.get('set_by', '')
            if not current_status.set_by and set_by:
                current_status.set_by = set_by
                current_status.save()
        
        logger.info('{} - Completed'.format(reach.name))

