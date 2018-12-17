import unittest

from ricochet import *

board = Board(9, 9, [], [Robot(5, 5)], Goal(6, 6))

def test_xy_conversions():
    for x in range(1, board.width + 1):
        for y in range(1 ,board.height + 1):
            assert board.position_to_xy(board.xy_to_position(x, y)) == (x, y)
    for pos in range(board.width * board.height):
        assert board.xy_to_position(*board.position_to_xy(pos)) == pos

def test_neighbours():
    assert board.neighbour(board.xy_to_position(1, 2), NORTH) == board.xy_to_position(1, 1)
    assert board.neighbour(board.xy_to_position(1, 1), NORTH) == -1
    assert board.neighbour(board.xy_to_position(1, 1), EAST) == board.xy_to_position(2, 1)
    assert board.neighbour(board.xy_to_position(9, 1), EAST) == -1
    assert board.neighbour(board.xy_to_position(5, 5), SOUTH) == board.xy_to_position(5, 6)
    assert board.neighbour(board.xy_to_position(5, 9), SOUTH) == -1
    assert board.neighbour(board.xy_to_position(5, 5), WEST) == board.xy_to_position(4, 5)
    assert board.neighbour(board.xy_to_position(1, 9), SOUTH) == -1

