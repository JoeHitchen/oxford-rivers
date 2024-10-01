from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail

from flags import models as flags

from .tasks import check_automated_flag
from . import models


mock_recipients = ['example@ourcs.org.uk', 'admin@mail.fantasybumps.org.uk']


@override_settings(AUTOFLAG_NOTIFICATION_RECIPIENTS = mock_recipients)
class Test__Automation(TestCase):
    fixtures = ['flags', 'autoflags']

    def setUp(self):
        self.autoflag = models.AutoFlag.objects.get(tag = 'godstow')  # Enabled & Grey by default
        self.autoflag.statuses.create(
            flag = flags.Status.Flags.RED,
            set_at = timezone.now() - timedelta(1),
        )


    def test__disabled(self):
        """No action is performed if the autoflag is disabled"""

        self.autoflag.enabled = False
        self.autoflag.save()

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'Disabled')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREY)
        self.assertEqual(len(mail.outbox), 0)
    

    @patch('automation.tasks.get_current_flag')
    def test__no_change(self, lookup_mock):
        """No change is reported if the status is unchanged"""

        lookup_mock.return_value = flags.Status.Flags.GREY

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'No Change')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREY)
        self.assertEqual(len(mail.outbox), 0)


    def test__ourcs_matches(self):
        """No change is reported if the new flag matches the OURCs flag"""

        self.autoflag.statuses.create(flag = flags.Status.Flags.GREEN, set_at = timezone.now())

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'No Notification')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)
        self.assertEqual(len(mail.outbox), 0)


    def test__ourcs_differs(self):
        """A change is reported if the status has changed"""

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'Notification')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, 'autoflag@mail.fantasybumps.org.uk')
        self.assertEqual(mail.outbox[0].to, mock_recipients)
        self.assertEqual(mail.outbox[0].subject, '[AutoFlag] Godstow: Green')
        self.assertEqual(
            mail.outbox[0].body,
            'According to the latest differentials, the Godstow flag is now Green',
        )

