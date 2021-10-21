from unittest.mock import patch
from datetime import datetime
import logging

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
import pytz

from .. import models
from .. import data

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
    
    
    @patch('flags.data.requests')
    @patch.object(models.Reach, 'update_flag_status')
    def test__success(self, update_mock, requests_mock):
        """Retrieves flag information from the OURCs API and updates the stored record."""
        
        set_date = timezone.now().isoformat()
        requests_mock.get.return_value.json.return_value = {
            'status': models.Status.Flags.BLUE,
            'set_date': set_date,
            'set_by': 'OURCs Committee Member',
        }
        
        data.fetch_ourcs_flag(self.reach)
        
        self.assertEqual(update_mock.call_count, 1)
        update_mock.assert_called_once_with(
            models.Status.Flags.BLUE,
            set_date,
            'OURCs Committee Member',
        )
    
    
    @patch('flags.data.requests')
    @patch.object(models.Reach, 'update_flag_status')
    def test__request_error(self, update_mock, requests_mock):
        """Raises an error if the API request is not successful."""
        
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = Exception
        
        with self.assertRaises(Exception):
            data.fetch_ourcs_flag(self.reach)
        
        self.assertEqual(requests_mock.get.return_value.raise_for_status.call_count, 1)
    
    
    @patch('flags.data.fetch_ourcs_flag')
    def test__management__success(self, fetch_ourcs_flag_mock):
        """Management command calls the data routine for both the Isis and Godstow."""
        
        call_command('fetch_ourcs_flags')
        
        self.assertEqual(fetch_ourcs_flag_mock.call_count, 2)
        fetch_ourcs_flag_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        fetch_ourcs_flag_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))
    
    
    @patch('flags.data.fetch_ourcs_flag')
    def test__management__error(self, fetch_ourcs_flag_mock):
        """Management command gracefully handles errors and always calls both reaches."""
        
        fetch_ourcs_flag_mock.side_effect = ValueError
        
        call_command('fetch_ourcs_flags')
        
        self.assertEqual(fetch_ourcs_flag_mock.call_count, 2)
        fetch_ourcs_flag_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        fetch_ourcs_flag_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))


class Test_OURCsFlagHistory(TestCase):
    fixtures = ['flags']
    
    @classmethod
    def setUpTestData(cls):
        cls.reach = models.Reach.objects.create(
            name = 'Test',
            tag = 'test',
            downstream_order = 1,
        )
        
        with open('flags/fixtures/IsisFlagHistory.html') as file:
            cls.page_contents = file.read()
    
    
    @patch('flags.data.requests')
    def test__success(self, requests_mock):
        """Retrieves flag information from the OURCs API and updates the stored record."""
        
        requests_mock.get.return_value.text = self.page_contents
        
        data.scrape_ourcs_flag_history(self.reach)
        self.assertEqual(self.reach.statuses.count(), 62)
    
    
    @patch('flags.data.requests')
    def test__no_duplication_on_rerun(self, requests_mock):
        """Running the routine twice should not result in duplications."""
        
        requests_mock.get.return_value.text = self.page_contents
        
        data.scrape_ourcs_flag_history(self.reach)
        data.scrape_ourcs_flag_history(self.reach)
        self.assertEqual(self.reach.statuses.count(), 62)
    
    
    @patch('flags.data.requests')
    def test__no_duplication_with_existing(self, requests_mock):
        """Existing records should not be duplicated.
        
        Seconds and milliseconds on the set_at time are ignored when comparing - See #23.
        """
        
        self.reach.statuses.create(  # This record matches the most recent record in the fixture
            flag = models.Status.Flags.GREEN,
            set_at = '2021-05-27T12:59:45.769200+01:00',
        )
        
        requests_mock.get.return_value.text = self.page_contents
        
        data.scrape_ourcs_flag_history(self.reach)
        self.assertEqual(self.reach.statuses.count(), 62)
    
    
    @patch('flags.data.requests')
    def test__request_error(self, requests_mock):
        """Raises an error if the API request is not successful."""
        
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = Exception
        
        with self.assertRaises(Exception):
            data.scrape_ourcs_flag_history(self.reach)
        
        self.assertEqual(requests_mock.get.return_value.raise_for_status.call_count, 1)
        self.assertEqual(self.reach.statuses.count(), 0)
    
    
    @patch('flags.data.scrape_ourcs_flag_history')
    def test__management__success(self, scrape_flag_history_mock):
        """Management command calls the data routine for both the Isis and Godstow."""
        
        call_command('scrape_ourcs_flag_history')
        
        self.assertEqual(scrape_flag_history_mock.call_count, 2)
        scrape_flag_history_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        scrape_flag_history_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))
    
    
    @patch('flags.data.scrape_ourcs_flag_history')
    def test__management__error(self, scrape_flag_history_mock):
        """Management command gracefully handles errors and always calls both reaches."""
        
        scrape_flag_history_mock.side_effect = ValueError
        
        call_command('scrape_ourcs_flag_history')
        
        self.assertEqual(scrape_flag_history_mock.call_count, 2)
        scrape_flag_history_mock.assert_any_call(models.Reach.objects.get(tag = 'isis'))
        scrape_flag_history_mock.assert_any_call(models.Reach.objects.get(tag = 'godstow'))


class Test_EABoards(TestCase):
    fixtures = ['flags']
    
    @classmethod
    def setUpTestData(cls):
        with open('flags/fixtures/RiverThamesConditions.html') as file:
            cls.page_contents = file.read()
    
    
    @patch('flags.data.requests')
    def test__request_error(self, requests_mock):
        """Throws an error when the page retrieval fails."""
        
        requests_mock.get.return_value.ok = False
        requests_mock.get.return_value.raise_for_status.side_effect = Exception
        
        with self.assertRaises(Exception):
            data.scrape_ea_boards()
        
        self.assertEqual(requests_mock.get.return_value.raise_for_status.call_count, 1)
    
    
    @patch('flags.data.requests')
    @patch.object(models.Reach, 'update_advisory')
    def test__success(self, update_mock, requests_mock):
        """Parses the EA page and updates each reach appropriately."""
        
        boards_shown = datetime(2020, 10, 30, 11, 15).astimezone(pytz.timezone('Europe/London'))
        reach_map = {reach.tag: reach for reach in models.Reach.objects.all()}
        requests_mock.get.return_value.text = self.page_contents
        
        data.scrape_ea_boards()
        
        self.assertEqual(update_mock.call_count, 6)
        update_mock.assert_any_call(reach_map['isis'], 'INC', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['godstow'], 'RED', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['radley'], 'DEC', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['abingdon'], 'NONE', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['wallingford'], 'INC', board_shown = boards_shown)
        update_mock.assert_any_call(reach_map['sandford'], 'DEC', board_shown = boards_shown)
        
        requests_mock.get.return_value.raise_for_status.assert_not_called()

