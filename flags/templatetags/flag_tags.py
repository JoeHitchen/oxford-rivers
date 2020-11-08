from django import template

from .. utils import Transit

register = template.Library()


@register.inclusion_tag(template.Template('''
            <div class="card-group">
              <div class="card mb-3" style="max-width: 7em;">
                <div class="card-body">{{ type }}</div>
              </div>
              <div
                class="card {{ text_colour }} {{ background_colour }} mb-3"
                style="max-width: 18rem;"
              >
                <div class="card-body">{{ main_text }}</div>
              </div>
            </div>
'''))
def transit_allowed_row(type, allowed):
    switch_selected = {
        Transit.PERMITTED: {
            'main_text': 'Allowed',
            'text_colour': 'text-light',
            'background_colour': 'bg-success',
        },
        Transit.RESTRICTIONS: {
            'main_text': 'Restrictions Apply',
            'text_colour': 'text-dark',
            'background_colour': 'bg-warning',
        },
        Transit.PROHIBITED: {
            'main_text': 'Not allowed',
            'text_colour': 'text-light',
            'background_colour': 'bg-danger',
        },
    }[allowed]
    return {'type': type, **switch_selected}


@register.inclusion_tag(template.Template('''
        {% load flag_tags %}
        <div class="card">
          <div class="card-header">
            {{ destination }} Transit
          </div>
          <div class="card-body">
            {% transit_allowed_row 'Boats' rowing %}{% transit_allowed_row 'Launches' launches %}
          </div>
        </div>
'''))
def transit_card(transit):
    return transit  # Implicitly destructures transit for context

