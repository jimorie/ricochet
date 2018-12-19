#!/usr/bin/env python

#
# Ricochet Robot Solver
#
# Well, almost! This solver does not feature an "active" robot. It will find
# the shortest solution that any robot can get to the goal. Adding the active
# criteria should be trivial, but that's just not how we've been playing it.
#

from re import compile as re_compile

from click import UsageError, command, option


NORTH      = 1 << 0
EAST       = 1 << 1
SOUTH      = 1 << 2
WEST       = 1 << 3
ROBOT      = 1 << 4
GOAL       = 1 << 5
DIRECTIONS = (NORTH, EAST, SOUTH, WEST)
DIRNAMES   = {NORTH: 'north', EAST: 'east', SOUTH: 'south', WEST: 'west'}
CHARDIRS   = {v[0]: k for k, v in DIRNAMES.items()}
FLIPDIRS   = {NORTH: SOUTH, EAST: WEST, SOUTH: NORTH, WEST: EAST}


class Board:
    def __init__(self, width, height, walls, robots, goal):
        self.width = width
        self.height = height
        self.positions = [0] * (self.width * self.height)
        self.robots = robots
        self.goal = goal
        for wall in walls:
            wall.place(self)
        for robot in robots:
            robot.place(self)
        goal.place(self)

    def add(self, placeable):
        self.positions[placeable.position] |= placeable.marker

    def remove(self, placeable):
        self.positions[placeable.position] &= ~placeable.marker

    def has(self, position, mask):
        return self.positions[position] & mask

    def neighbour(self, position, direction):
        if direction == NORTH:
            position -= self.width
            return position if position >= 0 else -1
        if direction == EAST:
            position += 1
            return position if position % self.width else -1
        if direction == SOUTH:
            position += self.width
            return position if position < self.width * self.height else -1
        if direction == WEST:
            return position - 1 if position % self.width else -1

    def trace(self, position, direction):
        blocker = ROBOT | FLIPDIRS[direction]
        while True:
            next_pos = self.neighbour(position, direction)
            if next_pos < 0 or self.has(next_pos, blocker):
                return position
            position = next_pos

    def possible_moves(self):
        for robot in self.robots:
            for direction in DIRECTIONS:
                stop_position = self.trace(robot.position, direction)
                if stop_position != robot.position:
                    yield Move(robot, direction, robot.position, stop_position)

    def robot_state(self):
        return tuple(sorted(robot.position for robot in self.robots))

    def check_xy(self, x, y):
        return 1 <= x <= self.width and 1 <= y <= self.height

    def xy_to_position(self, x, y):
        return (y - 1) * self.width + x - 1

    @staticmethod
    def xy_to_chess(x, y):
        return '{}{}'.format(chr(x + ord('a') - 1), y)

    def position_to_xy(self, position):
        return (position % self.width) + 1, (position // self.width) + 1

    def position_to_chess(self, position):
        return self.xy_to_chess(*self.position_to_xy(position))

    def search(self, min_moves, max_moves):
        self.moves = []
        self.states_of_despair = {}
        for remaining_moves in range(min_moves, max_moves + 1):
            if self.search_rec(remaining_moves):
                print('Solution found in {} moves!'.format(len(self.moves)))
                for move in self.moves:
                    move.announce()
                return
        print('No solution found in {} moves.'.format(max_moves))

    def search_rec(self, remaining_moves):
        current_state = self.robot_state()
        tried_moves = self.states_of_despair.get(current_state, 0)
        if tried_moves < remaining_moves:
            for move in self.possible_moves():
                move.execute()
                self.moves.append(move)
                if self.has(self.goal.position, ROBOT):
                    # We fucking did it!
                    return True
                if remaining_moves > 1 and self.search_rec(remaining_moves - 1):
                    return True
                self.moves.pop()
                move.undo()
            self.states_of_despair[current_state] = remaining_moves
        return False


class Placeable:
    _chess_regex = re_compile(r'([a-z])(\d+)(.*)')

    def __init__(self, x, y):
        self.start_xy = x, y
        self.position = None
        self.board = None

    @classmethod
    def from_string(cls, arg):
        m = cls._chess_regex.match(arg)
        if not m:
            raise UsageError('Bad board position: {}'.format(arg))
        obj = cls(ord(m.group(1)) - ord('a') + 1, int(m.group(2)))
        name = m.group(3).strip()
        if name:
            obj.name = name
        return obj

    @property
    def marker(self):
        raise NotImplementedError()

    def place(self, board):
        if not board.check_xy(*self.start_xy):
            raise UsageError(
                'Bad board position: {}'.format(
                    board.xy_to_chess(*self.start_xy)
                )
            )
        self.board = board
        self.position = self.board.xy_to_position(*self.start_xy)
        self.board.add(self)

    def neighbour(self, direction):
        return self.board.neighbour(self.position, direction)


class Wall(Placeable):
    _wall_regex = re_compile(r'([a-z])(\d+)(n|e|s|w)$')

    def __init__(self, x, y, direction, otherside=None):
        Placeable.__init__(self, x, y)
        self.direction = direction
        self.otherside = otherside

    @classmethod
    def from_string(cls, arg):
        m = cls._wall_regex.match(arg)
        if not m:
            raise UsageError('Bad wall position: {}'.format(arg))
        return cls(
            ord(m.group(1)) - ord('a') + 1,
            int(m.group(2)),
            CHARDIRS[m.group(3)]
        )

    @property
    def marker(self):
        return self.direction

    def place(self, board):
        Placeable.place(self, board)
        if self.otherside is None:
            other_x, other_y = board.position_to_xy(
                self.neighbour(self.direction)
            )
            self.otherside = Wall(
                other_x,
                other_y,
                FLIPDIRS[self.direction],
                otherside=self
            )
        if self.otherside:
            Placeable.place(self.otherside, board)


class Robot(Placeable):
    marker = ROBOT
    _robot_counter = 0

    def __init__(self, x, y):
        Robot._robot_counter += 1
        self.name = 'R{n}D{n}'.format(n=Robot._robot_counter)
        Placeable.__init__(self, x, y)

    def move(self, position):
        self.board.remove(self)
        self.position = position
        self.board.add(self)


class Goal(Placeable):
    marker = GOAL


class Move:
    def __init__(self, robot, direction, start_position, stop_position):
        self.robot = robot
        self.direction = direction
        self.start_position = start_position
        self.stop_position = stop_position

    def execute(self):
        self.robot.move(self.stop_position)

    def undo(self):
        self.robot.move(self.start_position)

    def announce(self):
        print('{} moves {}: {} => {}'.format(
            self.robot.name,
            DIRNAMES[self.direction],
            self.robot.board.position_to_chess(self.start_position),
            self.robot.board.position_to_chess(self.stop_position)
        ))


@command()
@option(
    '--width',
    type=int,
    default=9,
    required=False,
    help='Board width.'
)
@option(
    '--height',
    type=int,
    default=9,
    required=False,
    help='Board height.'
)
@option(
    '--min-moves',
    type=int,
    default=1,
    required=False,
    help='Starting search depth in number of moves. '
)
@option(
    '--max-moves',
    type=int,
    default=20,
    required=False,
    help='Maximum search depth in number of moves before giving up.'
)
@option(
    '--wall',
    '-w',
    'walls',
    type=Wall.from_string,
    multiple=True,
    required=False,
    help=(
        'Place a wall with chess notation plus a direction, i.e. a1n, b2w, '
        'etc. Mirror walls are placed automatically.'
    )
)
@option(
    '--robot',
    '-r',
    'robots',
    type=Robot.from_string,
    multiple=True,
    required=True,
    help=(
        'Place a robot with chess notation, i.e. a1, b2, etc. Additional '
        'characters are used as the robot name, if present.'
    )
)
@option(
    '--goal',
    '-g',
    type=Goal.from_string,
    required=True,
    help='Place the goal with chess notation, i.e. a1, b2, etc.'
)
def main(width, height, min_moves, max_moves, walls, robots, goal):
    board = Board(width, height, walls, robots, goal)
    board.search(min_moves, max(max_moves, min_moves))


if __name__ == '__main__':
    main()
