from datetime import timedelta

from django.shortcuts import render
from django.views.generic.detail import DetailView
from django.utils import timezone

from . import models, utils


def advisory_overview(request):
    reaches = models.Reach.objects.prefetch_related('advisories').all()
    reach_board_map = {reach.tag: reach.current_advisory.board for reach in reaches}
    
    context = {
        'reaches': reaches,
        'all_reaches': reaches,
        'transits': [
            utils.calculate_transit_permitted(
                reach_board_map,
                'Godstow',
                ['isis', 'godstow'],
            ),
            utils.calculate_transit_permitted(
                reach_board_map,
                'Radley',
                ['isis', 'sandford', 'radley'],
            ),
            utils.calculate_transit_permitted(
                reach_board_map,
                'Abingdon',
                ['isis', 'sandford', 'radley', 'abingdon'],
            ),
        ],
    }
    
    return render(request, 'flags/advisory_overview.html', context)


class AdvisoryHistory(DetailView):
    
    model = models.Reach
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/advisory_history.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_reaches'] = models.Reach.objects.all()
        
        time_since_last_update = timezone.now() - self.object.current_advisory.last_seen
        context['out_of_date'] = time_since_last_update > timedelta(hours = 2)
        return context

