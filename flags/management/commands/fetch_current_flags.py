import logging

from django.core.management.base import BaseCommand
import requests

from ... import models

logger = logging.getLogger('OURCs Flags')
logger.setLevel('INFO')


class Command(BaseCommand):
    help = 'Retrieves historical flag information from the OURCs website'
    
    def handle(self, *args, **kwargs):
        """Perform retrieval for both Isis and Godstow."""
        
        self.fetch_for_reach(models.Reach.objects.get(tag = 'isis'))
        self.fetch_for_reach(models.Reach.objects.get(tag = 'godstow'))
    
    
    @staticmethod
    def fetch_for_reach(reach):
        """Main loopup routine."""
        logger.info('{} - Fetching...'.format(reach.name))
        
        # Request and parse OURCs flag pages
        response = requests.get('https://ourcs.co.uk/api/flags/status/{}/'.format(reach.tag))
        if not response.ok:
            response.raise_for_status()
        response_json = response.json()
        
        # Flag changed
        if not reach.current_flag or response_json['status'] != reach.current_flag.flag:
            logger.info('{} - Changed from {} to {}'.format(
                reach.name,
                reach.current_flag and reach.current_flag.flag,
                response_json['status'],
            ))
            
            # Create new status
            reach.statuses.create(
                flag = response_json['status'],
                first_shown = response_json['set_date'],
                changed_by = response_json.get('set_by', ''),
            )
        
        # Flag unchanged
        else:
            logger.info('{} - Unchanged at {}'.format(reach.name, reach.current_flag.flag))
            
            # Add missing changed-by
            changed_by = response_json.get('set_by', '')
            if not reach.current_flag.changed_by and changed_by:
                reach.current_flag.changed_by = changed_by
                reach.current_flag.save()
        
        logger.info('{} - Completed'.format(reach.name))

