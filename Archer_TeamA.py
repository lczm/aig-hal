import typing
import pygame

from random import randint, random
from Graph import *
from Base import *

from Character import *
from State import *


class Archer_TeamA(Character):
    def __init__(self, world, image, projectile_image, base, position):
        Character.__init__(self, world, "archer", image)

        self.projectile_image = projectile_image

        self.base: Base = base
        self.position: Vector2 = position
        self.move_target: GameEntity = GameEntity(world, "archer_move_target", None)
        self.target: GameEntity = None

        self.maxSpeed: int = 50
        self.min_target_distance: int = 100
        self.projectile_range: int = 100
        self.projectile_speed: int = 100

        seeking_state: ArcherStateAttacking_TeamA = ArcherStateSeeking_TeamA(self)
        attacking_state: ArcherStateAttacking_TeamA = ArcherStateAttacking_TeamA(self)
        ko_state: ArcherStateKO_TeamA = ArcherStateKO_TeamA(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(ko_state)

        self.brain.set_state("seeking")

        self.time_passed: float = 0

    def render(self, surface):
        Character.render(self, surface)

    def process(self, time_passed) -> None:
        Character.process(self, time_passed)
        self.time_passed = time_passed

        level_up_stats: typing.List[str] = [
            "hp",
            "speed",
            "ranged damage",
            "ranged cooldown",
            "projectile range",
        ]

        if self.can_level_up():
            choice = randint(0, len(level_up_stats) - 1)
            self.level_up(level_up_stats[choice])


class ArcherStateSeeking_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "seeking")
        self.archer: Archer_TeamA = archer

        self.archer.path_graph = self.archer.world.paths[
            randint(0, len(self.archer.world.paths) - 1)
        ]

    def do_actions(self) -> None:
        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self) -> str:
        # check if opponent is in range
        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            opponent_distance = (
                self.archer.position - nearest_opponent.position
            ).length()
            if opponent_distance <= self.archer.min_target_distance:
                self.archer.target = nearest_opponent
                return "attacking"

        if (self.archer.position - self.archer.move_target.position).length() < 8:
            # continue on path
            if self.current_connection < self.path_length:
                self.archer.move_target.position = self.path[
                    self.current_connection
                ].toNode.position
                self.current_connection += 1

        return None

    def entry_actions(self) -> None:
        nearest_node = self.archer.path_graph.get_nearest_node(self.archer.position)
        self.path = pathFindAStar(
            self.archer.path_graph,
            nearest_node,
            self.archer.path_graph.nodes[self.archer.base.target_node_index],
        )

        self.path_length = len(self.path)
        if self.path_length > 0:
            self.current_connection = 0
            self.archer.move_target.position = self.path[0].fromNode.position
        else:
            self.archer.move_target.position = self.archer.path_graph.nodes[
                self.archer.base.target_node_index
            ].position


class ArcherStateAttacking_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "attacking")
        self.archer: Archer_TeamA = archer

    def do_actions(self):
        # TODO : Change target to the target that is closest to the archer
        # TODO : once changed, check surrounding radius by a certain amoutn
        # If enemy hp is (one-hit) status, change target to that
        opponent_distance = (
            self.archer.position - self.archer.target.position
        ).length()

        # if can attack
        if self.archer.current_ranged_cooldown <= 0:
            if opponent_distance <= self.archer.min_target_distance:
                self.archer.velocity = Vector2(0, 0)
                self.archer.ranged_attack(self.archer.target.position)
            else:
                self.archer.velocity = (
                    self.archer.target.position - self.archer.position
                )
        # cannot attack
        else:
            # if the current distance is more than what an archer can usually
            # hit from, with some padding
            # TODO : Store pathfinding graph in self.archer and use that to find
            # nearest node and kite back and forth
            # TODO (2) : (If the above is not implemented), can check that
            # the archer has stayed in the same spot for a frame, and generate a random
            # direction vector to move towards
            if opponent_distance > self.archer.min_target_distance + (
                self.archer.time_passed * self.archer.maxSpeed
            ):
                self.archer.velocity = (
                    self.archer.target.position - self.archer.position
                )
            else:
                self.archer.velocity = -(
                    self.archer.target.position - self.archer.position
                )

            if self.archer.velocity.length() > 0:
                self.archer.velocity.normalize_ip()
                self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self) -> str:
        # target is gone
        if (
            self.archer.world.get(self.archer.target.id) is None
            or self.archer.target.ko
        ):
            self.archer.target = None
            return "seeking"

        return None

    def entry_actions(self):
        return None


class ArcherStateKO_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "ko")
        self.archer: Archer_TeamA = archer

    def do_actions(self):
        return None

    def check_conditions(self) -> str:
        # respawned
        if self.archer.current_respawn_time <= 0:
            self.archer.current_respawn_time = self.archer.respawn_time
            self.archer.ko = False
            self.archer.path_graph = self.archer.world.paths[
                randint(0, len(self.archer.world.paths) - 1)
            ]
            return "seeking"
        return None

    def entry_actions(self):
        self.archer.current_hp = self.archer.max_hp
        self.archer.position = Vector2(self.archer.base.spawn_position)
        self.archer.velocity = Vector2(0, 0)
        self.archer.target = None
        return None
