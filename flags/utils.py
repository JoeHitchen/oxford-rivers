from . import models


class Transit:
    PERMITTED = 'PERMITTED'
    RESTRICTIONS = 'RESTRICTIONS'
    PROHIBITED = 'PROHIBITED'


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
            'rowing': Transit.PROHIBITED if any_not_green_flag else Transit.PERMITTED,
            'launches': Transit.PERMITTED,
        }
    
    # Some stream advisories
    return {
        'destination': destination,
        'rowing': Transit.PROHIBITED,
        'launches': Transit.PROHIBITED if any_red_boards else Transit.RESTRICTIONS,
    }

