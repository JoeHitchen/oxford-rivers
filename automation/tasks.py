from django.conf import settings
from django.core import mail

from flags import models as flags

from . import models


def get_current_flag(autoflag):  # To be replaced with a proper lookup
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

