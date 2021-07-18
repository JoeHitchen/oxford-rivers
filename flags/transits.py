from . import models


class Permissions:
    PERMITTED = 'PERMITTED'
    APPROVAL = 'APPROVAL'  # Indicates specific approval required
    PROHIBITED = 'PROHIBITED'


destination_reaches_map = {
    models.Reach.Common.GODS: [models.Reach.Common.ISIS, models.Reach.Common.GODS],
    models.Reach.Common.RAD: [
        models.Reach.Common.ISIS,
        models.Reach.Common.SAND,
        models.Reach.Common.RAD,
    ],
    models.Reach.Common.AB: [
        models.Reach.Common.ISIS,
        models.Reach.Common.SAND,
        models.Reach.Common.RAD,
        models.Reach.Common.AB,
    ],
}


def generate_transit_information(flag_reaches, board_reaches):
    """Calculates if the three hard-coded transits are permitted under the current river state."""
    
    permitted_flags = [models.Status.Flags.GREEN, models.Status.Flags.GREY]
    reach_flag_map = {
        reach.tag: reach.current_flag_status and reach.current_flag_status.flag
        for reach in flag_reaches
    }
    reach_board_map = {
        reach.tag: reach.current_advisory.board
        for reach in board_reaches
    }
    
    transits = []
    for destination, reaches in destination_reaches_map.items():
        
        flags = [reach_flag_map[reach] for reach in reaches if reach_flag_map.get(reach)]
        boards = [reach_board_map[reach] for reach in reaches]
        
        transits.append(describe_transit(
            destination = destination,
            all_boards_clear = all(board == models.Advisory.Boards.NONE for board in boards),
            any_red_boards = any(board == models.Advisory.Boards.RED for board in boards),
            any_not_green_flag = any(flag not in permitted_flags for flag in flags),
        ))
    
    return transits


def describe_transit(destination, all_boards_clear, any_red_boards, any_not_green_flag):
    """Converts a set of high-level river state flags into a Transit object."""
    
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
        'launches': Permissions.PROHIBITED if any_red_boards else Permissions.APPROVAL,
    }

