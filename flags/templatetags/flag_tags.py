from math import floor
from calendar import monthrange
import random

from django import template

from .. import models
from .. transits import Permissions

register = template.Library()


@register.filter
def subtract(a, b):
    return a - b


@register.filter
def flag_colour(flag):
    return {
        models.Status.Flags.GREY: 'bg-secondary',
        models.Status.Flags.GREEN: 'bg-success',
        models.Status.Flags.LIGHT: 'bg-lightblue',
        models.Status.Flags.BLUE: 'bg-primary',
        models.Status.Flags.AMBER: 'bg-warning',
        models.Status.Flags.RED: 'bg-danger',
        models.Status.Flags.BLACK: 'bg-dark',
    }[flag]


@register.filter
def advisory_colour(flag):
    return {
        models.Advisory.Boards.NONE: 'bg-success',
        models.Advisory.Boards.INC: 'bg-warning',
        models.Advisory.Boards.DEC: 'bg-warning',
        models.Advisory.Boards.RED: 'bg-danger',
        models.Advisory.Boards.OUT: 'bg-info',
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


@register.inclusion_tag('flag_tags/timeline_row.html')
def timeline_row(date, flag_reaches, all_reaches, first_row = False):
    return {
        'date': date,
        'flag_data': [random.choice(list(models.Status.Flags)) for reach in flag_reaches],
        'advisory_data': [random.choice(list(models.Advisory.Boards)) for reach in all_reaches],
        'show_date': date.day == monthrange(date.year, date.month)[1] or first_row,
    }

