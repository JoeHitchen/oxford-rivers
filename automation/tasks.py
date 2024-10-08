from django.conf import settings
from django.core import mail

from flags import models as flags
from jameson import models as jameson

from . import models


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

    return jameson.Differential.objects.using('jameson').filter(reach = reach)[0].differential


def get_current_flag(autoflag):

    boundaries = {
        flags.Reach.Common.ISIS: isis_boundaries,
        flags.Reach.Common.GODS: godstow_boundaries,
    }[flags.Reach.Common(autoflag.tag)]

    differential = get_current_differential(autoflag)
    for boundary, flag in boundaries:
        if differential >= boundary:
            return flag

    return flags.Status.Flags.GREEN


def check_automated_flag(reach_tag):

    autoflag = models.AutoFlag.objects.get(tag = reach_tag)
    if not autoflag.enabled:
        return 'Disabled'

    current_flag = get_current_flag(autoflag)
    if current_flag == autoflag.status:
        return 'No Change'

    autoflag.status = current_flag
    autoflag.save()

    if autoflag.status == autoflag.current_flag_status.flag:  # Compares with latest OURCs fetch
        return 'No Notification'
    
    mail.send_mail(
        f'[AutoFlag] {autoflag.tag.title()}: {autoflag.status.label}',
        (
            'According to the latest differentials, '
            f'the {autoflag.tag.title()} flag is now {autoflag.status.label}'
        ),
        'autoflag@mail.fantasybumps.org.uk',
        settings.AUTOFLAG_NOTIFICATION_RECIPIENTS,
    )
    return 'Notification'

