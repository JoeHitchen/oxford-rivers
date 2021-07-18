"""Tests all single-variable cases, but no multi-variable cases."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from flags import models, transits


class CommonSetup():
    fixtures = ['flags']
    
    @staticmethod
    def reach_queries():
        return (
            (
                models.Reach.objects
                .filter(has_ourcs_flag = True)
                .prefetch_related('statuses')
            ),
            models.Reach.objects.prefetch_related('advisories'),
        )
    
    
    @classmethod
    def setUpTestData(cls):
        for reach in models.Reach.objects.all():
            reach.update_advisory(
                models.Advisory.Boards.NONE,
                board_shown = timezone.now() - timedelta(1),
            )
        
        for reach in models.Reach.objects.filter(has_ourcs_flag = True):
            reach.update_flag_status(
                models.Status.Flags.GREEN,
                set_at = timezone.now() - timedelta(1),
            )


class Test_IsisFlag(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.isis = models.Reach.objects.get(tag = models.Reach.Common.ISIS)
    
    
    def test__green(self):
        """All transits allowed."""
        
        self.isis.update_flag_status(models.Status.Flags.GREEN, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__blue(self):
        """All rowing transits prohibited, all launch transits allowed."""
        
        self.isis.update_flag_status(models.Status.Flags.BLUE, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__amber(self):
        """All rowing transits prohibited, all launch transits allowed."""
        
        self.isis.update_flag_status(models.Status.Flags.AMBER, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """All rowing transits prohibited, all launch transits allowed."""
        
        self.isis.update_flag_status(models.Status.Flags.RED, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__black(self):
        """All rowing transits prohibited, all launch transits allowed."""
        
        self.isis.update_flag_status(models.Status.Flags.BLACK, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__grey(self):
        """All transits allowed."""
        
        self.isis.update_flag_status(models.Status.Flags.GREY, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_GodstowFlag(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.godstow = models.Reach.objects.get(tag = models.Reach.Common.GODS)
    
    
    def test__green(self):
        """All transits allowed."""
        
        self.godstow.update_flag_status(models.Status.Flags.GREEN, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__amber(self):
        """Rowing transits to Godstow prohibited, all other transits allowed."""
        
        self.godstow.update_flag_status(models.Status.Flags.AMBER, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """Rowing transits to Godstow prohibited, all other transits allowed."""
        
        self.godstow.update_flag_status(models.Status.Flags.RED, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__black(self):
        """Rowing transits to Godstow prohibited, all other transits allowed."""
        
        self.godstow.update_flag_status(models.Status.Flags.BLACK, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__grey(self):
        """All transits allowed."""
        
        self.godstow.update_flag_status(models.Status.Flags.GREY, set_at = timezone.now())
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_IsisBoards(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.isis = models.Reach.objects.get(tag = models.Reach.Common.ISIS)
    
    
    def test__none(self):
        """All transits allowed."""
        
        self.isis.update_advisory(models.Advisory.Boards.NONE)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_increasing(self):
        """All rowing transits prohibited, all launch transits allowed with approval."""
        
        self.isis.update_advisory(models.Advisory.Boards.INC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_decreasing(self):
        """All rowing transits prohibited, all launch transits allowed with approval."""
        
        self.isis.update_advisory(models.Advisory.Boards.DEC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """All transits prohibited."""
        
        self.isis.update_advisory(models.Advisory.Boards.RED)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_GodstowBoards(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.godstow = models.Reach.objects.get(tag = models.Reach.Common.GODS)
    
    
    def test__none(self):
        """All transits allowed."""
        
        self.godstow.update_advisory(models.Advisory.Boards.NONE)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_increasing(self):
        """Rowing transits to Godstow prohibited and launch transits require approval."""
        
        self.godstow.update_advisory(models.Advisory.Boards.INC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_decreasing(self):
        """Rowing transits to Godstow prohibited and launch transits require approval."""
        
        self.godstow.update_advisory(models.Advisory.Boards.DEC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """All transits to Godstow prohibited, all other transits allowed."""
        
        self.godstow.update_advisory(models.Advisory.Boards.RED)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_SandfordBoards(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.sand = models.Reach.objects.get(tag = models.Reach.Common.SAND)
    
    
    def test__none(self):
        """All transits allowed."""
        
        self.sand.update_advisory(models.Advisory.Boards.NONE)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_increasing(self):
        """Rowing transits downstream prohibited and launch transits require approval."""
        
        self.sand.update_advisory(models.Advisory.Boards.INC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_decreasing(self):
        """Rowing transits downstream prohibited and launch transits require approval."""
        
        self.sand.update_advisory(models.Advisory.Boards.DEC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """All downstream transits prohibited."""
        
        self.sand.update_advisory(models.Advisory.Boards.RED)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_RadleyBoards(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.radley = models.Reach.objects.get(tag = models.Reach.Common.RAD)
    
    
    def test__none(self):
        """All transits allowed."""
        
        self.radley.update_advisory(models.Advisory.Boards.NONE)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_increasing(self):
        """Rowing transits downstream prohibited and launch transits require approval."""
        
        self.radley.update_advisory(models.Advisory.Boards.INC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_decreasing(self):
        """Rowing transits downstream prohibited and launch transits require approval."""
        
        self.radley.update_advisory(models.Advisory.Boards.DEC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """All downstream transits prohibited, Godstow transits allowed."""
        
        self.radley.update_advisory(models.Advisory.Boards.RED)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_AbingdonBoards(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.abingdon = models.Reach.objects.get(tag = models.Reach.Common.AB)
    
    
    def test__none(self):
        """All transits allowed."""
        
        self.abingdon.update_advisory(models.Advisory.Boards.NONE)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_increasing(self):
        """Rowing transits to Abingdon prohibited and launch transits require approval."""
        
        self.abingdon.update_advisory(models.Advisory.Boards.INC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_decreasing(self):
        """Rowing transits to Abingdon prohibited and launch transits require approval."""
        
        self.abingdon.update_advisory(models.Advisory.Boards.DEC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.APPROVAL,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """All transits to Abingdon prohibited."""
        
        self.abingdon.update_advisory(models.Advisory.Boards.RED)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PROHIBITED,
                'launches': transits.Permissions.PROHIBITED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)


class Test_WallingfordBoards(CommonSetup, TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.walli = models.Reach.objects.get(tag = models.Reach.Common.WALLI)
    
    
    def test__none(self):
        """Wallingford boards do not affect any transits."""
        
        self.walli.update_advisory(models.Advisory.Boards.NONE)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_increasing(self):
        """Wallingford boards do not affect any transits."""
        
        self.walli.update_advisory(models.Advisory.Boards.INC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__yellow_decreasing(self):
        """Wallingford boards do not affect any transits."""
        
        self.walli.update_advisory(models.Advisory.Boards.DEC)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)
    
    
    def test__red(self):
        """Wallingford boards do not affect any transits."""
        
        self.walli.update_advisory(models.Advisory.Boards.RED)
        
        generated_info = transits.generate_transit_information(*self.reach_queries())
        expected_info = [
            {
                'destination': models.Reach.Common.GODS,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.RAD,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
            {
                'destination': models.Reach.Common.AB,
                'rowing': transits.Permissions.PERMITTED,
                'launches': transits.Permissions.PERMITTED,
            },
        ]
        
        self.assertEqual(generated_info, expected_info)

