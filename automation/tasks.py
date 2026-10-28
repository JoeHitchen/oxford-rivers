from datetime import timedelta
import logging

from django.conf import settings
from django.core import mail
from django.utils import timezone
from django.template.loader import render_to_string

from core import tasks_app
from flags import models as flags
from jameson import models as jameson

from . import models

logger = logging.getLogger('Automation')
logger.setLevel('INFO')


DIFFERENTIAL_TIME_WINDOW = timedelta(hours = 2)
DIFFERENTIAL_RANGE_WINDOW = (-0.15, 1.40)


class AutoFlagCheckOutput:
    DISABLED = 'Disabled'
    NO_CHANGE = 'No Change'
    NO_NOTIFY = 'No Notify'
    NOTIFY_FAILED = 'Failed Notify'
    NOTIFY = 'Notify'


isis_boundaries = [
    (0.720, flags.Status.Flags.BLACK),
    (0.535, flags.Status.Flags.RED),
    (0.442, flags.Status.Flags.AMBER),
    (0.330, flags.Status.Flags.BLUE),
    (0.215, flags.Status.Flags.LIGHT),
]

godstow_boundaries = [
    (0.75, flags.Status.Flags.RED),
    (0.45, flags.Status.Flags.AMBER),
]


def get_current_differential(autoflag):

    reach = {
        flags.Reach.Common.ISIS: jameson.Differential.Reach.ISIS,
        flags.Reach.Common.GODS: jameson.Differential.Reach.GODSTOW,
    }[flags.Reach.Common(autoflag.tag)]

    differentials = jameson.Differential.filter(
        reach = reach,
        time__range = (timezone.now() - DIFFERENTIAL_TIME_WINDOW, timezone.now()),
        differential__range = DIFFERENTIAL_RANGE_WINDOW,
    ).values_list('differential', flat = True)
    if len(differentials) == 0:
        raise jameson.Differential.DoesNotExist

    return sum(differentials) / len(differentials)


def get_current_flag(autoflag):

    try:
        differential = get_current_differential(autoflag)
    except jameson.Differential.DoesNotExist:
        return flags.Status.Flags.GREY

    boundaries = {
        flags.Reach.Common.ISIS: isis_boundaries,
        flags.Reach.Common.GODS: godstow_boundaries,
    }[flags.Reach.Common(autoflag.tag)]

    for boundary, flag in boundaries:
        if differential >= boundary:
            return flag

    return flags.Status.Flags.GREEN


@tasks_app.task
def check_automated_flag(reach_tag):

    no_action = '  ->  No further action required'

    # Retrieve the automated flag record
    autoflag = models.AutoFlag.objects.get(tag = reach_tag.lower())
    logger.info(f'AutoFlag - {autoflag.name} - Running automated flag indication...')
    if not autoflag.enabled:
        logger.info(f'AutoFlag - {autoflag.name} - Automated updates disabled' + no_action)
        return AutoFlagCheckOutput.DISABLED

    logger.info('AutoFlag - {} - Previous indication: {}'.format(
        autoflag.name,
        flags.Status.Flags(autoflag.status).label,
    ))


    # Determine if the flag has changed
    current_flag = get_current_flag(autoflag)
    if current_flag == autoflag.status:
        logger.info(f'AutoFlag - {autoflag.name} - Indication unchanged' + no_action)
        return AutoFlagCheckOutput.NO_CHANGE

    logger.info('AutoFlag - {} - Indication changed: {}'.format(
        autoflag.name,
        flags.Status.Flags(current_flag).label,
    ))
    autoflag.status = current_flag
    autoflag.save()


    # Compare with the latest OURCs flag retrieval
    if autoflag.status == autoflag.current_flag_status.flag:
        logger.info(f'AutoFlag - {autoflag.name} - Matches active OURCs flag' + no_action)
        return AutoFlagCheckOutput.NO_NOTIFY

    logger.info('AutoFlag - {} - Active OURCs flag differs: {}'.format(
        autoflag.name,
        flags.Status.Flags(autoflag.current_flag_status.flag).label,
    ))


    # Send a notification if a flag change is due
    mail_success = mail.send_mail(
        f'[AutoFlag] {autoflag.name}: {autoflag.status.label}',
        render_to_string('automation/flag_notification.txt', {'autoflag': autoflag}),
        'Flag Automation <autoflag@mail.fantasybumps.org.uk>',
        settings.AUTOFLAG_NOTIFICATION_RECIPIENTS,
    )
    if not mail_success:
        logger.error(f'AutoFlag - {autoflag.name} - Failed to send notification')
        return AutoFlagCheckOutput.NOTIFY_FAILED

    logger.info(f'AutoFlag - {autoflag.name} - Notification sent')
    return AutoFlagCheckOutput.NOTIFY


@tasks_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):

    autoflag_reaches = models.AutoFlag.objects.all()
    for reach in autoflag_reaches:
        sender.add_periodic_task(0.5 * 60, check_automated_flag.s(reach.tag.capitalize()))


