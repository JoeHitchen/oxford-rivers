from datetime import datetime
import logging

import requests

from . import models

logger = logging.getLogger('Data')
logger.setLevel('INFO')

API_ROOT = 'https://api.thameswater.co.uk/opendata/v2'


def fetch_thames_water_discharges():
    """Retrieves current discharge statuses from Thames Water and updates the stored events"""
    
    logger.info('Thames Water Discharges - Fetching...')
    
    # Request status of all stations
    response = requests.get(API_ROOT + '/discharge/status', timeout = 60)
    if not response.ok:
        logger.error('Thames Water Discharges - Error fetching statuses')
        response.raise_for_status()
    reports = {
        item['permitNumber']: item
        for item in response.json()['items']
        if 'permitNumber' in item
    }
    
    # Update monitored stations
    for station in models.Station.objects.all():
        try:
            status = None
            status_changed = None

            if station.permit_number in reports:
                status = reports[station.permit_number]['alertStatus']
                logger.info('Thames Water Discharges - {} - {}'.format(station, status))

                raw_status_changed = reports[station.permit_number]['statusChanged']
                status_changed = datetime.fromisoformat(f'{raw_status_changed}Z')

            else:
                logger.warning('Thames Water Discharges - {} - Not in response'.format(station))

            station.update_discharge_status(status, status_changed)

        except Exception:
            logger.exception('Thames Water Discharges - {} - Unable to process'.format(station))

    logger.info('Thames Water Discharges - Completed')
    return models.Station.summary()
