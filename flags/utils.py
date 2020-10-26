from . import models

class Transit:
    PERMITTED = 'PERMITTED'
    RESTRICTIONS = 'RESTRICTIONS'
    PROHIBITED = 'PROHIBITED'


def calculate_transit_permitted(reach_board_map, destination, reach_tags):
    boards = [reach_board_map[tag] for tag in reach_tags]
    any_red_boards = any(board == models.Advisory.Boards.RED for board in boards)
    all_boards_clear = all(board == models.Advisory.Boards.NONE for board in boards)
    
    return {
        'destination': destination,
        'rowing': Transit.RESTRICTIONS if all_boards_clear else Transit.PROHIBITED,
        'launches': Transit.PROHIBITED if any_red_boards else ( Transit.PERMITTED if all_boards_clear else Transit.RESTRICTIONS ),
    }

