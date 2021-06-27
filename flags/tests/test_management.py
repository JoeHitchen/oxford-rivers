from unittest.mock import patch
from datetime import datetime
import logging

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
import pytz

from .. import models
from ..management.commands.fetch_ourcs_flags import Command as FetchOURCsFlags

logging.disable(logging.CRITICAL)


class Test_OURCsFlag(TestCase):
    fixtures = ['flags']
    
    @classmethod
    def setUpTestData(cls):
        cls.reach = models.Reach.objects.create(
            name = 'Test',
            tag = 'test',
            downstream_order = 1,
        )
        cls.set_at = timezone.now()
        cls.set_by = 'OURCs Committee Member'
    
    
    def setUp(self):
        """ Clear cache - Weird things happen if removed"""
        self.reach.current_flag_status
        del self.reach.current_flag_status
    
    
    @patch.object(FetchOURCsFlags, 'fetch_for_reach')
    def test__handle__success(self, fetch_for_reach_mock):
        """Calls the subroutine for both the Isis and Godstow."""
        
        call_command('fetch_ourcs_flags')
        
        self.assertEqual(fetch_for_reach_mock.call_count, 2)
        fetch_for_reach_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        fetch_for_reach_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))
    
    
    @patch.object(FetchOURCsFlags, 'fetch_for_reach')
    def test__handle__error(self, fetch_for_reach_mock):
        """Gracefully handles errors in any of the reach calls and still calls both reaches."""
        
        fetch_for_reach_mock.side_effect = ValueError
        
        call_command('fetch_ourcs_flags')
        
        self.assertEqual(fetch_for_reach_mock.call_count, 2)
        fetch_for_reach_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        fetch_for_reach_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))
    
    
    @patch('flags.management.commands.fetch_ourcs_flags.requests')
    @patch.object(models.Reach, 'update_flag_status')
    def test__fetch__success(self, update_mock, requests_mock):
        """Retrieves flag information from the OURCs API and updates the stored record."""
        
        set_date = timezone.now().isoformat()
        requests_mock.get.return_value.json.return_value = {
            'status': models.Status.Flags.BLUE,
            'set_date': set_date,
            'set_by': 'OURCs Committee Member',
        }
        
        FetchOURCsFlags.fetch_for_reach(self.reach)
        
        self.assertEqual(update_mock.call_count, 1)
        update_mock.assert_called_once_with(
            models.Status.Flags.BLUE,
            set_date,
            'OURCs Committee Member',
        )
    
    
    @patch('flags.management.commands.fetch_ourcs_flags.requests')
    @patch.object(models.Reach, 'update_flag_status')
    def test__fetch__request_error(self, update_mock, requests_mock):
        """Raises an error if the request is not successful."""
        
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = Exception
        
        with self.assertRaises(Exception):
            FetchOURCsFlags.fetch_for_reach(self.reach)
        
        self.assertEqual(requests_mock.get.return_value.raise_for_status.call_count, 1)


class Test_EABoards(TestCase):
    fixtures = ['flags']
    
    @classmethod
    def setUpTestData(cls):
        with open('flags/fixtures/RiverThamesConditions.html') as file:
            cls.page_contents = file.read()
    
    
    @patch('flags.management.commands.scrape_ea_boards.requests')
    def test__fetch_error(self, requests_mock):
        """Throws an error when the page retrieval fails."""
        
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = Exception
        
        with self.assertRaises(Exception):
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

