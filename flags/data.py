from datetime import datetime, timedelta
import logging
import zoneinfo
import re

from django.utils import timezone
from bs4 import BeautifulSoup
import requests

from . import models

logger = logging.getLogger('Data')
logger.setLevel('INFO')


board_regex_map = {
    'no(.*)warning': models.Advisory.Boards.NONE,
    'yellow(.*)inc': models.Advisory.Boards.INC,
    'yellow(.*)dec': models.Advisory.Boards.DEC,
    'red': models.Advisory.Boards.RED,
}


def fetch_ourcs_flag(reach):
    """Retrieves current flag information from the OURCs APIs"""
    
    logger.info('OURCs Flag - {} - Fetching...'.format(reach.name))
    
    # Request and parse OURCs flag APIs
    response = requests.get('https://ourcs.co.uk/api/flags/status/{}/'.format(reach.tag))
    if not response.ok:
        response.raise_for_status()
    response_json = response.json()
    
    # Update and log flag status
    if response_json['status'] == 'H':
        response_json['status'] = models.Status.Flags.BLUE.value
    flag = models.Status.Flags(response_json['status'])
    reach.update_flag_status(flag, response_json['set_date'], response_json.get('set_by', ''))
    logger.info('OURCs Flag - {} - {}'.format(reach.name, flag.label))
    
    return flag


def scrape_ourcs_flag_history(reach):
    """Retrieves historical flag information from the OURCs website"""
    
    flag_text_map = {
        'Grey': models.Status.Flags.GREY,
        'Green': models.Status.Flags.GREEN,
        'Light Blue': models.Status.Flags.LIGHT,
        'Blue': models.Status.Flags.BLUE,
        'Dark Blue': models.Status.Flags.BLUE,
        'Amber': models.Status.Flags.AMBER,
        'Red': models.Status.Flags.RED,
        'Black': models.Status.Flags.BLACK,
    }
    
    
    # Request and parse OURCs flag pages
    response = requests.get('https://ourcs.co.uk/information/flags/{}/'.format(reach.tag))
    if not response.ok:
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Retrieve existing status records
    already_recorded = [
        (status.flag, status.set_at.replace(second = 0, microsecond = 0))
        for status in reach.statuses.all()
    ]
    
    # Iterate over historical statuses
    statuses = []
    previous_status_flag = None
    for status_row in soup.find_all('table')[2].contents[3].find_all('tr')[::-1]:
        
        # Extract status information
        status_row_elements = status_row.find_all('td')
        status_flag = flag_text_map[status_row_elements[0].contents[0]]
        
        status_start_string = status_row_elements[1].contents[0]
        status_start_naive = datetime.strptime(status_start_string, '%d/%m/%y %H:%M')
        status_start_aware = status_start_naive.astimezone(zoneinfo.ZoneInfo('Europe/London'))
        
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
            first_seen = status_start_aware,
        ))
    
    # Store all statuses
    models.Status.objects.bulk_create(statuses)
    
    # Fudge last-seen data
    prev_set = timezone.now()
    statuses = list(reach.statuses.all())
    for status in statuses:
        if status.last_seen >= prev_set:
            status.last_seen = max(prev_set - timedelta(minutes = 2), status.first_seen)
        prev_set = status.first_seen
    models.Status.objects.bulk_update(statuses, ['last_seen'])


def _extract_ea_board(main_column, reach):
    """Extracts the board for a reach, or indicates an outage."""

    # Extract the boards
    try:
        lock_search_string = f'{reach.upstream_lock} Lock to {reach.downstream_lock} Lock'
        reach_row = main_column.find(string = lock_search_string).parent.parent
        board_text = reach_row.contents[3].contents[0].lower()

        for regex, board in board_regex_map.items():
            if re.search(regex, board_text):
                return board

        assert False, 'No regular expression matched'

    # Indicate an outage on failure
    except Exception as err:
        logger.error(f'Board Parsing Error: {err.__str__()}')
        return models.Advisory.Boards.OUT


def scrape_ea_boards():
    """Retrieves stream advisory boards from the EA website"""
    
    # Request and parse EA Boards page
    response = requests.get('https://www.gov.uk/guidance/river-thames-current-river-conditions')
    if not response.ok:
        logger.error('EA Boards - Error fetching page')
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract last-updated datetime
    last_updated_element = soup.find(attrs = {'name': 'govuk:updated-at'})
    last_updated = datetime.fromisoformat(last_updated_element['content'])
    last_updated = last_updated.astimezone(zoneinfo.ZoneInfo('Europe/London'))
    logger.info('EA Boards - Last updated {}'.format(last_updated))
    
    # Extract boards
    boards = {}
    main_column = soup.find(class_ = 'govspeak')
    for reach in models.Reach.objects.all():
        board = _extract_ea_board(main_column, reach)
        logger.info('EA Boards - {:11s} - {}'.format(
            str(reach),
            models.Advisory.Boards(board).label),
        )
        
        models.Reach.update_advisory(reach, board, board_shown = last_updated)
        # ^ Class method used for testing purposes
        
        boards[reach] = models.Advisory.Boards(board)
    
    logger.info('EA Boards - Completed')
    return boards


