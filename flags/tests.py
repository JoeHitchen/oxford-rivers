from django.test import TestCase

from . import models, utils


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

