from datetime import datetime, timedelta
import logging

from django.utils import timezone
from bs4 import BeautifulSoup
import requests
import pytz

from . import models

logger = logging.getLogger('Data')
logger.setLevel('INFO')


def fetch_ourcs_flag(reach):
    """Retrieves current flag information from the OURCs APIs"""
    
    logger.info('OURCs Flag - {} - Fetching...'.format(reach.name))
    
    # Request and parse OURCs flag APIs
    response = requests.get('https://ourcs.co.uk/api/flags/status/{}/'.format(reach.tag))
    if not response.ok:
        response.raise_for_status()
    response_json = response.json()
    
    # Update and log flag status
    flag = models.Status.Flags(response_json['status'])
    reach.update_flag_status(flag, response_json['set_date'], response_json.get('set_by', ''))
    logger.info('OURCs Flag - {} - {}'.format(reach.name, flag.label))
    
    return flag


def scrape_ourcs_flag_history(reach):
    """Retrieves historical flag information from the OURCs website
    
    **UNTESTED** - This command is not expected to be called regularly."""
    
    flag_text_map = {
        'Grey': models.Status.Flags.GREY,
        'Green': models.Status.Flags.GREEN,
        'Blue': models.Status.Flags.BLUE,
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


def scrape_ea_boards():
    """Retrieves stream advisory boards from the EA website"""
    
    board_text_map = {
        'no stream warnings': models.Advisory.Boards.NONE,
        'caution stream increasing': models.Advisory.Boards.INC,
        'caution stream decreasing': models.Advisory.Boards.DEC,
        'caution strong stream': models.Advisory.Boards.RED,
    }
    
    def extract_board(main_column, downstream_lock):
        """Extracts the board for a reach above a specific lock."""
        
        reach_row = main_column.find(text = downstream_lock + ' Lock').parent.parent.parent
        board_outer = reach_row.contents[1].contents[0]
        board_inner = board_outer.contents[0].contents[0].contents[0].contents[0]
        
        return board_text_map[board_inner.lower()]
    
    
    # Request and parse EA Boards page
    response = requests.get('http://riverconditions.environment-agency.gov.uk/')
    if not response.ok:
        logger.error('EA Boards - Error fetching page')
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract last-updated datetime
    last_updated_element = soup.find(class_ = 'last-update')
    last_updated_string = last_updated_element.contents[0].split(': ')[1]
    last_updated = datetime.strptime(last_updated_string, '%d %B %Y %H:%M')
    last_updated = last_updated.astimezone(pytz.timezone('Europe/London'))
    logger.info('EA Boards - Last updated {}'.format(last_updated))
    
    # Extract boards
    boards = {}
    main_column = soup.find(class_ = 'primary-column')
    for reach in models.Reach.objects.all():
        board = extract_board(main_column, reach.downstream_lock)
        logger.info('EA Boards - {:11s} - {}'.format(
            str(reach),
            models.Advisory.Boards(board).label),
        )
        
        models.Reach.update_advisory(reach, board, board_shown = last_updated)
        # ^ Class method used for testing purposes
        
        boards[reach] = models.Advisory.Boards(board)
    
    logger.info('EA Boards - Completed')
    return boards


