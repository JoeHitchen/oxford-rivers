from django.test import TestCase

from flags import models, transits


class Test_TransitPermitted(TestCase):
    
    DEST = 'Destination'
    REACH_A = 'reach_a'
    REACH_B = 'reach_b'
    
    def test__no_board(self):
        """Launches can transit, and rowing boats can with restrictions, if no boards shown."""
        
        transit_object = transits.calculate_transit_permitted(
            {},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PERMITTED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__yellow_inc(self):
        """Only launches (with restrictions) can transit under yellow boards."""
        
        transit_object = transits.calculate_transit_permitted(
            {},
            {self.REACH_A: models.Advisory.Boards.INC},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.RESTRICTIONS,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__yellow_dec(self):
        """Only launches (with restrictions) can transit under yellow boards."""
        
        transit_object = transits.calculate_transit_permitted(
            {},
            {self.REACH_A: models.Advisory.Boards.DEC},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.RESTRICTIONS,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__red_board(self):
        """Transits are not permitted under red boards."""
        
        transit_object = transits.calculate_transit_permitted(
            {},
            {self.REACH_A: models.Advisory.Boards.RED},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.PROHIBITED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__extra_mapped_reach(self):
        """Reaches in the map but not in the transit are not considered."""
        
        transit_object = transits.calculate_transit_permitted(
            {},
            {self.REACH_A: models.Advisory.Boards.NONE, self.REACH_B: models.Advisory.Boards.RED},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PERMITTED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__two_reaches(self):
        """Multiple reaches can be listed and considered."""
        
        reach_board_map = {
            self.REACH_A: models.Advisory.Boards.NONE,
            self.REACH_B: models.Advisory.Boards.RED,
        }
        transit_object = transits.calculate_transit_permitted(
            {},
            reach_board_map,
            self.DEST,
            [self.REACH_A, self.REACH_B],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.PROHIBITED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__green_flag(self):
        """Green flag does not prevent transits."""
        
        transit_object = transits.calculate_transit_permitted(
            {self.REACH_A: models.Status.Flags.GREEN},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PERMITTED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__blue_flag(self):
        """Blue flag prevents transits."""
        
        transit_object = transits.calculate_transit_permitted(
            {self.REACH_A: models.Status.Flags.BLUE},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__amber_flag(self):
        """Amber flag prevents transits."""
        
        transit_object = transits.calculate_transit_permitted(
            {self.REACH_A: models.Status.Flags.AMBER},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__red_flag(self):
        """Red flag prevents transits."""
        
        transit_object = transits.calculate_transit_permitted(
            {self.REACH_A: models.Status.Flags.RED},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__black_flag(self):
        """Black flag prevents transits."""
        
        transit_object = transits.calculate_transit_permitted(
            {self.REACH_A: models.Status.Flags.BLACK},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PROHIBITED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)
    
    
    def test__grey_flag(self):
        """Grey flag does not prevent transits."""
        
        transit_object = transits.calculate_transit_permitted(
            {self.REACH_A: models.Status.Flags.GREY},
            {self.REACH_A: models.Advisory.Boards.NONE},
            self.DEST,
            [self.REACH_A],
        )
        expected_object = {
            'destination': self.DEST,
            'rowing': transits.Transit.PERMITTED,
            'launches': transits.Transit.PERMITTED,
        }
        self.assertEqual(transit_object, expected_object)

