from unittest.mock import patch
from datetime import timedelta
import logging

from django.test import TestCase
from django.utils import timezone
from django.core.management import call_command

from . import models, utils

logging.disable(logging.CRITICAL)


class Test_Models_Reach(TestCase):
    fixtures = ['flags']
    
    def setUp(self):
        self.reach = models.Reach.objects.first()
        self.right_now = timezone.now()
        self.updated_time = self.right_now - timedelta(minutes = 17)
        self.original_time = self.right_now - timedelta(hours = 29)
    
    
    def test__update_advisory__no_previous(self):
        """Creates a new advisory."""
        
        # Prepare & run
        self.assertIsNone(self.reach.current_advisory)
        
        self.reach.update_advisory(models.Advisory.Boards.INC, board_shown = self.updated_time)
        
        # Check new advisory
        self.assertIsNotNone(self.reach.current_advisory)
        self.assertTrue(self.reach.current_advisory.first_seen > self.right_now)
        self.assertEqual(self.reach.current_advisory.first_updated, self.updated_time)
        self.assertTrue(self.reach.current_advisory.last_seen > self.right_now)
        self.assertEqual(self.reach.current_advisory.last_updated, self.updated_time)
    
    
    def test__update_advisory__different_advisory(self):
        """Creates a new advisory, leaving the previous advisory unchanged."""
        
        # Prepare & run
        previous_advisory = self.reach.advisories.create(
            board = models.Advisory.Boards.INC,
            first_seen = self.original_time,
            first_updated = self.original_time,
            last_seen = self.original_time,
            last_updated = self.original_time,
        )
        self.assertEqual(self.reach.current_advisory, previous_advisory)
        
        self.reach.update_advisory(models.Advisory.Boards.RED, board_shown = self.updated_time)
        
        # Check previous advisory
        previous_advisory.refresh_from_db()
        self.assertNotEqual(self.reach.current_advisory, previous_advisory)
        self.assertEqual(previous_advisory.first_seen, self.original_time)
        self.assertEqual(previous_advisory.first_updated, self.original_time)
        self.assertEqual(previous_advisory.last_seen, self.original_time)
        self.assertEqual(previous_advisory.last_updated, self.original_time)
        
        # Check new advisory
        self.assertIsNotNone(self.reach.current_advisory)
        self.assertTrue(self.reach.current_advisory.first_seen > self.right_now)
        self.assertEqual(self.reach.current_advisory.first_updated, self.updated_time)
        self.assertTrue(self.reach.current_advisory.last_seen > self.right_now)
        self.assertEqual(self.reach.current_advisory.last_updated, self.updated_time)
    
    
    def test__update_advisory__same_advisory(self):
        """The `last_seen` and `last_updated` fields of the current advisory should be updated."""
        
        # Prepare & run
        previous_advisory = self.reach.advisories.create(
            board = models.Advisory.Boards.RED,
            first_seen = self.original_time,
            first_updated = self.original_time,
            last_seen = self.original_time,
            last_updated = self.original_time,
        )
        self.assertEqual(self.reach.current_advisory, previous_advisory)
        
        self.reach.update_advisory(models.Advisory.Boards.RED, board_shown = self.updated_time)
        
        # Check previous advisory
        previous_advisory.refresh_from_db()
        self.assertEqual(self.reach.current_advisory, previous_advisory)
        self.assertEqual(previous_advisory.first_seen, self.original_time)
        self.assertEqual(previous_advisory.first_updated, self.original_time)
        self.assertTrue(previous_advisory.last_seen > self.right_now)
        self.assertEqual(previous_advisory.last_updated, self.updated_time)


class Test_Utils(TestCase):
    
    DEST = 'Destination'
    REACH_A = 'reach_a'
    REACH_B = 'reach_b'
    
    def test__transit_permitted__no_board(self):
        """Launches can transit, and rowing boats can with restrictions, if no boards shown."""
        
        transit_object = utils.calculate_transit_permitted(
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': utils.Transit.RESTRICTIONS,
            'launches': utils.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__transit_permitted__yellow_inc(self):
        """Only launches (with restrictions) can transit under yellow boards."""
        
        transit_object = utils.calculate_transit_permitted(
            {self.REACH_A: models.Advisory.Boards.INC},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': utils.Transit.PROHIBITED,
            'launches': utils.Transit.RESTRICTIONS,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__transit_permitted__yellow_dec(self):
        """Only launches (with restrictions) can transit under yellow boards."""
        
        transit_object = utils.calculate_transit_permitted(
            {self.REACH_A: models.Advisory.Boards.DEC},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': utils.Transit.PROHIBITED,
            'launches': utils.Transit.RESTRICTIONS,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__transit_permitted__red_board(self):
        """Transits are not permitted under red boards."""
        
        transit_object = utils.calculate_transit_permitted(
            {self.REACH_A: models.Advisory.Boards.RED},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': utils.Transit.PROHIBITED,
            'launches': utils.Transit.PROHIBITED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__transit_permitted__extra_mapped_reach(self):
        """Reaches in the map but not in the transit are not considered."""
        
        transit_object = utils.calculate_transit_permitted(
            {self.REACH_A: models.Advisory.Boards.NONE, self.REACH_B: models.Advisory.Boards.RED},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': utils.Transit.RESTRICTIONS,
            'launches': utils.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__transit_permitted__two_reaches(self):
        """Multiple reaches can be listed and considered."""
        
        reach_board_map = {
            self.REACH_A: models.Advisory.Boards.NONE,
            self.REACH_B: models.Advisory.Boards.RED,
        }
        transit_object = utils.calculate_transit_permitted(
            reach_board_map,
            self.DEST,
            [self.REACH_A, self.REACH_B],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': utils.Transit.PROHIBITED,
            'launches': utils.Transit.PROHIBITED,
        }
        self.assertEqual(transit_object, expected_object)


class Test_Management_EABoards(TestCase):
    fixtures = ['flags']
    
    
    @patch('flags.management.commands.scrape_ea_boards.randrange', return_value = 35)
    @patch('flags.management.commands.scrape_ea_boards.sleep')
    def test__with_delay(self, sleep_mock, range_mock):
        """Generates a random delay between 60 and 180 seconds."""
        
        call_command('scrape_ea_boards', '--delay')
        
        range_mock.assert_called_once_with(60, 180)
        sleep_mock.assert_called_once_with(35)

