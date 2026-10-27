from datetime import datetime
import logging
import zoneinfo

from django.db import models as django_models
import requests

from . import models

logger = logging.getLogger('Data')
logger.setLevel('INFO')

API_ROOT = 'https://api.thameswater.co.uk/opendata/v2'


class AlertStatus(django_models.TextChoices):
    DISCHARGING = 'Discharging'
    NOT_DISCHARGING = 'Not discharging'
    OFFLINE = 'Offline'


def parse_time(value):
    """Converts a Thames Water timestamp to an aware datetime.
    
    The API provides timestamps without an offset, which are assumed to be Europe/London local
    time. This is the only place that assumption is made.
    """
    return datetime.fromisoformat(value).replace(tzinfo = zoneinfo.ZoneInfo('Europe/London'))


def fetch_thames_water_discharges():
    """Retrieves current discharge statuses from Thames Water and updates the stored events"""
    
    logger.info('Thames Water Discharges - Fetching...')
    
    # Request status of all monitors
    response = requests.get(API_ROOT + '/discharge/status', timeout = 60)
    if not response.ok:
        logger.error('Thames Water Discharges - Error fetching statuses')
        response.raise_for_status()
    monitors = {item['permitNumber']: item for item in response.json()['items']}
    
    # Update monitored stations
    discharging = []
    for station in models.Station.objects.all():
        monitor = monitors.get(station.permit_number)
        if monitor is None:
            logger.warning('Thames Water Discharges - {} - Not in response'.format(station))
            continue
        
        status = AlertStatus(monitor['alertStatus'])
        status_changed = parse_time(monitor['statusChanged'])
        
        if status == AlertStatus.DISCHARGING:
            station.record_discharging(status_changed)
            discharging.append(station)
        elif status == AlertStatus.NOT_DISCHARGING:
            station.record_not_discharging(status_changed)
        # Offline monitors are deliberately ignored
        
        logger.info('Thames Water Discharges - {} - {}'.format(station, status.label))
    
    return discharging
