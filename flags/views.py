from django.shortcuts import render
from django.views.generic.detail import DetailView
from django.utils import timezone

from . import models, utils


class FlagHistory(DetailView):
    
    model = models.Reach
    queryset = models.Reach.objects.filter(has_ourcs_flag = True).prefetch_related('statuses')
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/flag_history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timezone_now'] = timezone.now()
        return context


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
    queryset = models.Reach.objects.prefetch_related('advisories')
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/advisory_history.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_reaches'] = models.Reach.objects.all()
        return context

