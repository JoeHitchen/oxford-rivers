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
        
        try:
            self.fetch_for_reach(models.Reach.objects.get(tag = 'isis'))
        except Exception as err:
            logger.error('Isis flag error')
            logger.exception(err)
        
        try:
            self.fetch_for_reach(models.Reach.objects.get(tag = 'godstow'))
        except Exception as err:
            logger.error('Godstow flag error')
            logger.exception(err)
    
    
    @staticmethod
    def fetch_for_reach(reach):
        """Main lookup routine."""
        logger.info('{} - Fetching...'.format(reach.name))
        
        # Request and parse OURCs flag APIs
        response = requests.get('https://ourcs.co.uk/api/flags/status/{}/'.format(reach.tag))
        if not response.ok:
            response.raise_for_status()
        response_json = response.json()
        
        # Update and log flag status
        flag = models.Status.Flags(response_json['status'])
        reach.update_flag_status(flag, response_json['set_date'], response_json.get('set_by', ''))
        logger.info('{} - {}'.format(reach.name, flag.label))

