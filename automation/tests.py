from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail

from flags import models as flags

from .tasks import AutoFlagCheckOutput, check_automated_flag, get_current_flag
from . import models


mock_recipients = ['example@ourcs.org.uk', 'admin@mail.fantasybumps.org.uk']


@patch('automation.tasks.get_current_differential', return_value = 0.37)
@override_settings(AUTOFLAG_NOTIFICATION_RECIPIENTS = mock_recipients)
class Test__Automation(TestCase):
    fixtures = ['flags', 'autoflags']

    def setUp(self):
        self.autoflag = models.AutoFlag.objects.get(tag = 'godstow')  # Enabled & Grey by default
        self.autoflag.statuses.create(
            flag = flags.Status.Flags.RED,
            set_at = timezone.now() - timedelta(1),
        )


    def test__disabled(self, _differential_mock):
        """No action is performed if the autoflag is disabled"""

        self.autoflag.enabled = False
        self.autoflag.save()

        output = check_automated_flag('godstow')
        self.assertEqual(output, AutoFlagCheckOutput.DISABLED)

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREY)
        self.assertEqual(len(mail.outbox), 0)
    

    @patch('automation.tasks.get_current_flag')
    def test__no_change(self, lookup_mock, _differential_mock):
        """No change is reported if the status is unchanged"""

        lookup_mock.return_value = flags.Status.Flags.GREY

        output = check_automated_flag('godstow')
        self.assertEqual(output, AutoFlagCheckOutput.NO_CHANGE)

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREY)
        self.assertEqual(len(mail.outbox), 0)


    def test__ourcs_matches(self, _differential_mock):
        """No change is reported if the new flag matches the OURCs flag"""

        self.autoflag.statuses.create(flag = flags.Status.Flags.GREEN, set_at = timezone.now())

        output = check_automated_flag('godstow')
        self.assertEqual(output, AutoFlagCheckOutput.NO_NOTIFY)

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)
        self.assertEqual(len(mail.outbox), 0)


    def test__ourcs_differs(self, _differential_mock):
        """A change is reported if the status has changed"""

        output = check_automated_flag('godstow')
        self.assertEqual(output, AutoFlagCheckOutput.NOTIFY)

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].from_email,
            'Flag Automation <autoflag@mail.fantasybumps.org.uk>',
        )
        self.assertEqual(mail.outbox[0].to, mock_recipients)
        self.assertEqual(mail.outbox[0].subject, '[AutoFlag] Godstow: Green')
        self.assertIn('the Godstow flag is now Green', mail.outbox[0].body)
        self.assertIn('https://flags.jamesonlee.com/godstow', mail.outbox[0].body)


    def test__isis(self, _differential_mock):
        """A change is reported if the status has changed"""

        isis = models.AutoFlag.objects.get(tag = 'isis')  # Enabled & Grey by default
        isis.statuses.create(flag = flags.Status.Flags.RED, set_at = timezone.now() - timedelta(1))

        output = check_automated_flag('isis')
        self.assertEqual(output, AutoFlagCheckOutput.NOTIFY)

        isis.refresh_from_db()
        self.assertEqual(isis.status, flags.Status.Flags.BLUE)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].from_email,
            'Flag Automation <autoflag@mail.fantasybumps.org.uk>',
        )
        self.assertEqual(mail.outbox[0].to, mock_recipients)
        self.assertEqual(mail.outbox[0].subject, '[AutoFlag] The Isis: Blue')
        self.assertIn('the Isis flag is now Blue', mail.outbox[0].body)
        self.assertIn('https://flags.jamesonlee.com/isis', mail.outbox[0].body)


class Test__GetCurrentFlag(TestCase):
    fixtures = ['flags', 'autoflags']

    def setUp(self):
        self.autoflag = models.AutoFlag.objects.get(tag = 'godstow')

    def test__isis(self):
        """Tests the flag calculation for the Isis"""

        isis_autoflag = models.AutoFlag.objects.get(tag = 'isis')
        isis_cases = [
            (0.05, flags.Status.Flags.GREEN),
            (0.20, flags.Status.Flags.GREEN),
            (0.22, flags.Status.Flags.LIGHT),
            (0.24, flags.Status.Flags.LIGHT),
            (0.31, flags.Status.Flags.LIGHT),
            (0.33, flags.Status.Flags.BLUE),
            (0.35, flags.Status.Flags.BLUE),
            (0.43, flags.Status.Flags.BLUE),
            (0.45, flags.Status.Flags.AMBER),
            (0.47, flags.Status.Flags.AMBER),
            (0.52, flags.Status.Flags.AMBER),
            (0.54, flags.Status.Flags.RED),
            (0.56, flags.Status.Flags.RED),
            (0.70, flags.Status.Flags.RED),
            (0.72, flags.Status.Flags.BLACK),
            (0.74, flags.Status.Flags.BLACK),
            (0.99, flags.Status.Flags.BLACK),
        ]

        for differential, expected_flag in isis_cases:
            with self.subTest(differential):
                with patch('automation.tasks.get_current_differential') as differential_mock:
                    differential_mock.return_value = differential

                    self.assertEqual(get_current_flag(isis_autoflag), expected_flag)

    def test__godstow(self):
        """Tests the flag calculation for Godstow"""

        godstow_autoflag = models.AutoFlag.objects.get(tag = 'godstow')
        godstow_cases = [
            (0.05, flags.Status.Flags.GREEN),
            (0.43, flags.Status.Flags.GREEN),
            (0.45, flags.Status.Flags.AMBER),
            (0.47, flags.Status.Flags.AMBER),
            (0.73, flags.Status.Flags.AMBER),
            (0.75, flags.Status.Flags.RED),
            (0.77, flags.Status.Flags.RED),
            (0.99, flags.Status.Flags.RED),
        ]

        for differential, expected_flag in godstow_cases:
            with self.subTest(differential):
                with patch('automation.tasks.get_current_differential') as differential_mock:
                    differential_mock.return_value = differential

                    self.assertEqual(get_current_flag(godstow_autoflag), expected_flag)

