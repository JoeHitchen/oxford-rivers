from django import template

from .. utils import Transit

register = template.Library()


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

