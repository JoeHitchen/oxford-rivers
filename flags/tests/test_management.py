from unittest.mock import patch
from datetime import datetime

from django.test import TestCase
from django.core.management import call_command
import pytz

from .. import models


class Test_EABoards(TestCase):
    fixtures = ['flags']
    
    @classmethod
    def setUpTestData(cls):
        with open('flags/fixtures/RiverThamesConditions.html') as file:
            cls.page_contents = file.read()
    
    
    @patch('flags.management.commands.scrape_ea_boards.requests')
    def test__fetch_error(self, requests_mock):
        """Throws an error when the page retrieval fails."""
        
        requests_mock.get.return_value.text = self.page_contents
        requests_mock.get.return_value.ok = False
        
        call_command('scrape_ea_boards')
        
        self.assertEqual(requests_mock.get.return_value.raise_for_status.call_count, 1)
    
    
    @patch('flags.management.commands.scrape_ea_boards.requests')
    @patch.object(models.Reach, 'update_advisory')
    @patch('flags.management.commands.scrape_ea_boards.randrange', return_value = 35)
    @patch('flags.management.commands.scrape_ea_boards.sleep')
    def test__standard(self, sleep_mock, range_mock, update_mock, requests_mock):
        """Parses the EA page and updates each reach appropriately."""
        
        boards_shown = datetime(2020, 10, 30, 11, 15).astimezone(pytz.timezone('Europe/London'))
        reach_map = {reach.tag: reach for reach in models.Reach.objects.all()}
        requests_mock.get.return_value.text = self.page_contents
        
        call_command('scrape_ea_boards')
        
        self.assertEqual(update_mock.call_count, 6)
        update_mock.assert_any_call(reach_map['isis'], 'INC', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['godstow'], 'RED', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['radley'], 'DEC', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['abingdon'], 'NONE', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['wallingford'], 'INC', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['sandford'], 'DEC', board_shown = boards_shown)
        
        requests_mock.get.return_value.raise_for_status.assert_not_called()
        range_mock.assert_not_called()
        sleep_mock.assert_not_called()
    
    
    @patch('flags.management.commands.scrape_ea_boards.requests')
    @patch('flags.management.commands.scrape_ea_boards.randrange', return_value = 35)
    @patch('flags.management.commands.scrape_ea_boards.sleep')
    def test__with_delay(self, sleep_mock, range_mock, requests_mock):
        """Generates a random delay between 60 and 180 seconds."""
        
        requests_mock.get.return_value.text = self.page_contents
        
        call_command('scrape_ea_boards', '--delay')
        
        range_mock.assert_called_once_with(60, 180)
        sleep_mock.assert_called_once_with(35)

