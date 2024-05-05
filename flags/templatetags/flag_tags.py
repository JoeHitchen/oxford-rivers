from math import floor
from calendar import monthrange

from django import template

from .. import models
from .. transits import Permissions

register = template.Library()


@register.filter
def subtract(a, b):
    return a - b


@register.filter
def is_month_end(date):
    return date.day == monthrange(date.year, date.month)[1]


@register.filter
def get_reach_flag(data, reach):
    return data.get('statuses', {}).get(reach, models.Status.Flags.OUTAGE)


@register.filter
def get_reach_advisory(data, reach):
    return data.get('advisories', {}).get(reach, models.Advisory.Boards.OUT)


@register.filter
def flag_colour(flag):
    return {
        models.Status.Flags.GREY: 'ourcs-grey',
        models.Status.Flags.GREEN: 'ourcs-green',
        models.Status.Flags.LIGHT: 'ourcs-light-blue',
        models.Status.Flags.BLUE: 'ourcs-blue',
        models.Status.Flags.AMBER: 'ourcs-amber',
        models.Status.Flags.RED: 'ourcs-red',
        models.Status.Flags.BLACK: 'ourcs-black',
        models.Status.Flags.OUTAGE: 'ourcs-outage',
    }[flag]


@register.filter
def advisory_colour(flag):
    return {
        models.Advisory.Boards.NONE: 'ea-clear',
        models.Advisory.Boards.INC: 'ea-yellow',
        models.Advisory.Boards.DEC: 'ea-yellow',
        models.Advisory.Boards.RED: 'ea-red',
        models.Advisory.Boards.OUT: 'ea-outage',
    }[flag]


@register.filter
def duration_days_hours(duration):
    
    str = ''
    if duration.days > 1:
        str = '{} days, '.format(duration.days)
    elif duration.days == 1:
        str = '1 day, '
    
    hours = floor(duration.total_seconds() / 60**2 - 24 * duration.days)
    str += '{} hour{}'.format(hours, 's' if hours > 1 else '')
    
    return str


@register.inclusion_tag(template.Template('''
              <tr>
                <td style="width: 33%{% if first %}; border-top: 0{% endif %}">
                  {{ type }}
                </td>
                <td
                  class="{{ text_colour }} {{ background_colour }}"{% if first %}
                  style="border-top: 0"{% endif %}
                >
                  {{ main_text }}
                </td>
              </tr>
'''))
def transit_allowed_row(type, allowed, first = False):
    switch_selected = {
        Permissions.PERMITTED: {
            'main_text': 'Allowed',
            'text_colour': 'text-light',
            'background_colour': 'bg-success',
        },
        Permissions.APPROVAL: {
            'main_text': 'Approval required',
            'text_colour': 'text-dark',
            'background_colour': 'bg-warning',
        },
        Permissions.PROHIBITED: {
            'main_text': 'Not allowed',
            'text_colour': 'text-light',
            'background_colour': 'bg-danger',
        },
    }[allowed]
    return {'type': type, 'first': first, **switch_selected}

