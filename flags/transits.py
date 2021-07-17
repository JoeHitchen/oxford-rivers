from . import models


class Permissions:
    PERMITTED = 'PERMITTED'
    RESTRICTIONS = 'RESTRICTIONS'
    PROHIBITED = 'PROHIBITED'


def generate_transit_information(flag_reaches, board_reaches):
    
    reach_flag_map = {
        reach.tag: reach.current_flag_status and reach.current_flag_status.flag
        for reach in flag_reaches
    }
    reach_board_map = {
        reach.tag: reach.current_advisory.board
        for reach in board_reaches
    }
    
    return [
        calculate_transit_permitted(
            reach_flag_map,
            reach_board_map,
            'Godstow',
            [models.Reach.Common.ISIS, models.Reach.Common.GODS],
        ),
        calculate_transit_permitted(
            reach_flag_map,
            reach_board_map,
            'Radley',
            [models.Reach.Common.ISIS, models.Reach.Common.SAND, models.Reach.Common.RAD],
        ),
        calculate_transit_permitted(
            reach_flag_map,
            reach_board_map,
            'Abingdon',
            [
                models.Reach.Common.ISIS,
                models.Reach.Common.SAND,
                models.Reach.Common.RAD,
                models.Reach.Common.AB,
            ],
        ),
    ]


def calculate_transit_permitted(reach_flag_map, reach_board_map, destination, reach_tags):
    """Indicates if rowing boats and/or launches are allowed to perform the transit described."""
    
    flags = [reach_flag_map[tag] for tag in reach_tags if tag in reach_flag_map]
    boards = [reach_board_map[tag] for tag in reach_tags]
    permitted_flags = [models.Status.Flags.GREEN, models.Status.Flags.GREY]
    
    any_not_green_flag = any(flag not in permitted_flags for flag in flags)
    any_red_boards = any(board == models.Advisory.Boards.RED for board in boards)
    all_boards_clear = all(board == models.Advisory.Boards.NONE for board in boards)
    
    # No stream advisories
    if all_boards_clear:
        return {
            'destination': destination,
            'rowing': Permissions.PROHIBITED if any_not_green_flag else Permissions.PERMITTED,
            'launches': Permissions.PERMITTED,
        }
    
    # Some stream advisories
    return {
        'destination': destination,
        'rowing': Permissions.PROHIBITED,
        'launches': Permissions.PROHIBITED if any_red_boards else Permissions.RESTRICTIONS,
    }

