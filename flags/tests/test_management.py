from unittest.mock import patch
from datetime import datetime, timedelta
import logging

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
import pytz

from .. import models
from ..management.commands.fetch_current_flags import Command as FetchCurrentFlags

logging.disable(logging.CRITICAL)


class Test_CurrentFlag(TestCase):
    fixtures = ['flags']
    
    @classmethod
    def setUpTestData(cls):
        cls.reach = models.Reach.objects.create(
            name = 'Test',
            tag = 'test',
            downstream_order = 1,
        )
        cls.first_shown = timezone.now()
        cls.changed_by = 'OURCs Committee Member'
    
    
    def setUp(self):
        """ Clear cache - Weird things happen if removed"""
        self.reach.current_flag
        del self.reach.current_flag
    
    
    @patch.object(FetchCurrentFlags, 'fetch_for_reach')
    def test__handle(self, fetch_for_reach_mock):
        """Calls the subroutine for both the Isis and Godstow."""
        
        call_command('fetch_current_flags')
        
        self.assertEqual(fetch_for_reach_mock.call_count, 2)
        fetch_for_reach_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        fetch_for_reach_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))
    
    
    @patch('flags.management.commands.fetch_current_flags.requests')
    def test__no_current_flag(self, requests_mock):
        """Creates a new flag status if none is present."""
        
        self.assertIsNone(self.reach.current_flag)
        
        requests_mock.get.return_value.json.return_value = {
            'status': models.Status.Flags.GREEN,
            'set_date': self.first_shown.isoformat(),
            'set_by': self.changed_by,
        }
        
        FetchCurrentFlags.fetch_for_reach(self.reach)
        
        del self.reach.current_flag  # Clear cache
        self.assertEqual(self.reach.current_flag.flag, models.Status.Flags.GREEN)
        self.assertEqual(self.reach.current_flag.first_shown, self.first_shown)
        self.assertEqual(self.reach.current_flag.changed_by, self.changed_by)
    
    
    @patch('flags.management.commands.fetch_current_flags.requests')
    def test__no_change(self, requests_mock):
        """No action is taken if the flag and changed-by fields match."""
        
        previous_flag = self.reach.statuses.create(
            flag = models.Status.Flags.GREEN,
            first_shown = self.first_shown,
        )
        self.assertEqual(previous_flag, self.reach.current_flag)
        
        requests_mock.get.return_value.json.return_value = {
            'status': models.Status.Flags.GREEN,
            'set_date': self.first_shown.isoformat(),
        }
        
        FetchCurrentFlags.fetch_for_reach(self.reach)
        
        del self.reach.current_flag  # Clear cache
        self.assertEqual(previous_flag, self.reach.current_flag)
    
    
    @patch('flags.management.commands.fetch_current_flags.requests')
    def test__add_changed_by(self, requests_mock):
        """No action is taken if the flag and changed-by fields match."""
        
        previous_flag = self.reach.statuses.create(
            flag = models.Status.Flags.GREEN,
            first_shown = self.first_shown,
        )
        self.assertEqual(self.reach.current_flag.changed_by, '')
        
        requests_mock.get.return_value.json.return_value = {
            'status': models.Status.Flags.GREEN,
            'set_date': self.first_shown.isoformat(),
            'set_by': self.changed_by,
        }
        
        FetchCurrentFlags.fetch_for_reach(self.reach)
        
        del self.reach.current_flag  # Clear cache
        self.assertEqual(previous_flag, self.reach.current_flag)
        self.assertEqual(self.reach.current_flag.changed_by, self.changed_by)
    
    
    @patch('flags.management.commands.fetch_current_flags.requests')
    def test__flag_changed(self, requests_mock):
        """A new status should be created when a different flag is seen."""
        
        previous_flag = self.reach.statuses.create(
            flag = models.Status.Flags.BLUE,
            first_shown = self.first_shown - timedelta(1),
        )
        self.assertEqual(previous_flag, self.reach.current_flag)
        
        requests_mock.get.return_value.json.return_value = {
            'status': models.Status.Flags.GREEN,
            'set_date': self.first_shown.isoformat(),
            'set_by': self.changed_by,
        }
        
        FetchCurrentFlags.fetch_for_reach(self.reach)
        
        del self.reach.current_flag  # Clear cache
        self.assertNotEqual(previous_flag, self.reach.current_flag)
        self.assertEqual(self.reach.current_flag.flag, models.Status.Flags.GREEN)
        self.assertEqual(self.reach.current_flag.first_shown, self.first_shown)
        self.assertEqual(self.reach.current_flag.changed_by, self.changed_by)


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

