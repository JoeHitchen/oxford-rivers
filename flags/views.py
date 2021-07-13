from django.views.generic import TemplateView
from django.views.generic.detail import DetailView

from . import models, utils


class FlagNavMixin:
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'all_reaches': models.Reach.objects.all(),
            'flag_reaches': models.Reach.objects.filter(has_ourcs_flag = True).order_by('pk'),
        })
        return context


class Index(FlagNavMixin, TemplateView):
    
    template_name = 'flags/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['all_reaches'] = context['all_reaches'].prefetch_related('advisories')
        context['flag_reaches'] = context['flag_reaches'].prefetch_related('statuses')
        reach_flag_map = {
            reach.tag: reach.current_flag_status and reach.current_flag_status.flag
            for reach in context['flag_reaches']
        }
        reach_board_map = {
            reach.tag: reach.current_advisory.board
            for reach in context['all_reaches']
        }
        
        context['transits'] = [
            utils.calculate_transit_permitted(
                reach_flag_map,
                reach_board_map,
                'Godstow',
                ['isis', 'godstow'],
            ),
            utils.calculate_transit_permitted(
                reach_flag_map,
                reach_board_map,
                'Radley',
                ['isis', 'sandford', 'radley'],
            ),
            utils.calculate_transit_permitted(
                reach_flag_map,
                reach_board_map,
                'Abingdon',
                ['isis', 'sandford', 'radley', 'abingdon'],
            ),
        ]
        
        return context


class FlagHistory(FlagNavMixin, DetailView):
    
    model = models.Reach
    queryset = models.Reach.objects.filter(has_ourcs_flag = True).prefetch_related('statuses')
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/flag_history.html'


class AdvisoryHistory(FlagNavMixin, DetailView):
    
    model = models.Reach
    queryset = models.Reach.objects.prefetch_related('advisories')
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/advisory_history.html'

