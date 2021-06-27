from math import floor

from django import template

from .. utils import Transit

register = template.Library()


@register.filter
def subtract(a, b):
    return a - b


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
        Transit.PERMITTED: {
            'main_text': 'Allowed',
            'text_colour': 'text-light',
            'background_colour': 'bg-success',
        },
        Transit.RESTRICTIONS: {
            'main_text': 'With Restrictions',
            'text_colour': 'text-dark',
            'background_colour': 'bg-warning',
        },
        Transit.PROHIBITED: {
            'main_text': 'Not allowed',
            'text_colour': 'text-light',
            'background_colour': 'bg-danger',
        },
    }[allowed]
    return {'type': type, 'first': first, **switch_selected}

