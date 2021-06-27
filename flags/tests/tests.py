from datetime import timedelta

from django.test import TestCase, tag
from django.utils import timezone
from django.urls import reverse

from .. import models, utils


class Test_Models_Reach(TestCase):
    fixtures = ['flags']
    
    def setUp(self):
        self.reach = models.Reach.objects.first()
        self.right_now = timezone.now() - timedelta(seconds = 1)  # Altered to avoid race condition
        self.updated_time = self.right_now - timedelta(minutes = 17)
        self.original_time = self.right_now - timedelta(hours = 29)
    
    
    def test__current_flag(self):
        """Selects the most recent status by set-at."""
        
        self.reach.statuses.create(  # Created before, set before
            flag = models.Status.Flags.GREEN,
            set_at = self.original_time - timedelta(4),
        )
        current = self.reach.statuses.create(  # Set most recently
            flag = models.Status.Flags.BLUE,
            set_at = self.original_time,
        )
        self.reach.statuses.create(  # Created after, set before
            flag = models.Status.Flags.AMBER,
            set_at = self.original_time - timedelta(2),
        )
        
        self.assertEqual(self.reach.current_flag_status, current)
    
    
    def test__current_advisory(self):
        """Selects the most recent advisory by first-updated."""
        
        self.reach.advisories.create(  # Created before, set before
            board = models.Advisory.Boards.NONE,
            first_updated = self.original_time - timedelta(4),
        )
        current = self.reach.advisories.create(  # Set most recently
            board = models.Advisory.Boards.INC,
            first_updated = self.original_time,
        )
        self.reach.advisories.create(  # Created after, set before
            board = models.Advisory.Boards.DEC,
            first_updated = self.original_time - timedelta(2),
        )
        
        self.assertEqual(self.reach.current_advisory, current)
    
    
    def test__update_flag_status__no_previous(self):
        """Creates a new flag status."""
        
        # Prepare & run
        self.assertIsNone(self.reach.current_flag_status)
        
        self.reach.update_flag_status(models.Status.Flags.BLUE, set_at = self.updated_time)
        
        # Check new advisory
        self.assertIsNotNone(self.reach.current_flag_status)
        self.assertEqual(self.reach.current_flag_status.flag, models.Status.Flags.BLUE)
        self.assertEqual(self.reach.current_flag_status.set_at, self.updated_time)
        self.assertTrue(self.reach.current_flag_status.first_seen > self.right_now)
        self.assertTrue(self.reach.current_flag_status.last_seen > self.right_now)
    
    
    def test__update_flag_status__different_flag(self):
        """Creates a new flag status, leaving the previous flag status unchanged."""
        
        # Prepare & run
        previous_status = self.reach.statuses.create(
            flag = models.Status.Flags.GREEN,
            set_at = self.original_time,
            first_seen = self.original_time,
            last_seen = self.original_time,
        )
        self.assertEqual(self.reach.current_flag_status, previous_status)
        
        self.reach.update_flag_status(models.Status.Flags.BLUE, set_at = self.updated_time)
        
        # Check previous status
        previous_status.refresh_from_db()
        self.assertNotEqual(self.reach.current_advisory, previous_status)
        self.assertEqual(previous_status.flag, models.Status.Flags.GREEN)
        self.assertEqual(previous_status.set_at, self.original_time)
        self.assertEqual(previous_status.first_seen, self.original_time)
        self.assertEqual(previous_status.last_seen, self.original_time)
        
        # Check new status
        self.assertIsNotNone(self.reach.current_flag_status)
        self.assertEqual(self.reach.current_flag_status.flag, models.Status.Flags.BLUE)
        self.assertEqual(self.reach.current_flag_status.set_at, self.updated_time)
        self.assertTrue(self.reach.current_flag_status.first_seen > self.right_now)
        self.assertTrue(self.reach.current_flag_status.last_seen > self.right_now)
    
    
    def test__update_flag_status__same_flag(self):
        """Updates the `last_seen` field when the flag is unchanged."""
        
        # Prepare & run
        previous_status = self.reach.statuses.create(
            flag = models.Status.Flags.GREEN,
            set_at = self.original_time,
            first_seen = self.original_time,
            last_seen = self.original_time,
        )
        self.assertEqual(self.reach.current_flag_status, previous_status)
        
        self.reach.update_flag_status(models.Status.Flags.GREEN, set_at = self.updated_time)
        
        # Check previous & current status
        previous_status.refresh_from_db()
        self.assertEqual(self.reach.current_flag_status, previous_status)
        self.assertEqual(previous_status.flag, models.Status.Flags.GREEN)
        self.assertEqual(previous_status.set_at, self.original_time)
        self.assertEqual(previous_status.first_seen, self.original_time)
        self.assertTrue(previous_status.last_seen > self.right_now)
    
    
    def test__update_flag_status__add_set_by(self):
        """Adds missing `set_by` data if the flag is unchanged."""
        
        # Prepare & run
        previous_status = self.reach.statuses.create(
            flag = models.Status.Flags.GREEN,
            set_at = self.original_time,
        )
        self.assertEqual(self.reach.current_flag_status, previous_status)
        self.assertEqual(previous_status.set_by, '')
        
        self.reach.update_flag_status(
            models.Status.Flags.GREEN,
            set_at = self.updated_time,
            set_by = 'OURCs Committee Member',
        )
        
        # Check previous & current status
        previous_status.refresh_from_db()
        self.assertEqual(self.reach.current_flag_status, previous_status)
        self.assertEqual(previous_status.set_by, 'OURCs Committee Member')
    
    
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
    
    
    def test__update_advisory__updated_in_future(self):
        """Accepts and updates the current advisory for updates which occur in the future.
        
        The EA clocks cannot be trusted - See issue #1.
        """
        
        # Prepare & run
        previous_advisory = self.reach.advisories.create(
            board = models.Advisory.Boards.INC,
            first_seen = self.original_time,
            first_updated = self.original_time,
            last_seen = self.original_time,
            last_updated = self.original_time,
        )
        self.assertEqual(self.reach.current_advisory, previous_advisory)
        
        future_time = timezone.now() + timedelta(minutes = 20)
        self.reach.update_advisory(
            models.Advisory.Boards.RED,
            board_shown = future_time,
        )
        
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
        self.assertEqual(self.reach.current_advisory.first_updated, future_time)
        self.assertTrue(self.reach.current_advisory.last_seen > self.right_now)
        self.assertEqual(self.reach.current_advisory.last_updated, future_time)


class Test_Models_Advisory(TestCase):
    fixtures = ['flags']
    
    def setUp(self):
        self.reach = models.Reach.objects.get(tag = 'isis')
    
    def test__out_of_date__in_date(self):
        """Advisories last seen within two hours are considered 'in date'."""
        
        advisory = self.reach.advisories.create(
            board = models.Advisory.Boards.NONE,
            last_seen = timezone.now() - timedelta(minutes = 119),
        )
        self.assertFalse(advisory.out_of_date)
    
    
    def test__out_of_date__too_old(self):
        """Advisories last seen over two hours ago are considered 'out of date'."""
        
        advisory = self.reach.advisories.create(
            board = models.Advisory.Boards.NONE,
            last_seen = timezone.now() - timedelta(minutes = 121),
        )
        self.assertTrue(advisory.out_of_date)


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


class Test_Views(TestCase):
    fixtures = ['flags']
    
    def setUp(self):
        self.reach = models.Reach.objects.get(tag = 'isis')
        
        for reach in models.Reach.objects.all():
            reach.update_advisory(
                models.Advisory.Boards.NONE,
                board_shown = timezone.now() - timedelta(reach.id * 11),
            )
            reach.update_advisory(
                models.Advisory.Boards.RED,
                board_shown = timezone.now() - timedelta(reach.id * 7),
            )
    
    
    def test__advisory_overview__response(self):
        """Lists all the reaches and generates a 200 response."""
        
        response = self.client.get(reverse('flags:advisory_overview'))
        
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['reaches'], models.Reach.objects.all())
        self.assertQuerysetEqual(response.context['all_reaches'], models.Reach.objects.all())
    
    
    @tag('query-count')
    def test__advisory_overview__query_count(self):
        """Expect:
            (1) SELECT reaches
            (1) PREFETCH advisories
        """
        
        with self.assertNumQueries(2):
            self.client.get(reverse('flags:advisory_overview'))
    
    
    def test__advisory_history__response(self):
        """Identifies the correct reach and generates a 200 response."""
        
        self.reach.current_advisory.last_seen = timezone.now() - timedelta(minutes = 115)
        self.reach.current_advisory.save()
        
        response = self.client.get(reverse(
            'flags:advisory_history',
            kwargs = {'tag': self.reach.tag},
        ))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['reach'], self.reach)
        
        self.assertQuerysetEqual(response.context['all_reaches'], models.Reach.objects.all())
    
    
    @tag('query-count')
    def test__advisory_history__query_count(self):
        """Expect:
            (1) SELECT reach
            (1) PREFETCH all advisories for reach
            (1) SELECT all reaches
        """
        
        with self.assertNumQueries(3):
            self.client.get(reverse(
                'flags:advisory_history',
                kwargs = {'tag': self.reach.tag},
            ))

