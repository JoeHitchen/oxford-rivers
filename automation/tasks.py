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
    
    return 'Change'

