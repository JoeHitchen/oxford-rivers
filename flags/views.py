from django.shortcuts import render

from . import models, utils


def index(request):
    reaches = models.Reach.objects.prefetch_related('advisories').all()
    reach_board_map = {reach.tag: reach.current_advisory.board for reach in reaches}
    
    context = {
        'reaches': reaches,
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
    
    return render(request, 'flags/index.html', context)

