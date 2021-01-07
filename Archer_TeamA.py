import pygame

from random import randint, random
from typing import List
from Graph import *
from Base import *

from Character import *
from State import *

"""
    TODO : Strategy for levelling up stats
    TODO : Fleeing state
    TODO : Fleeing(?), strategy for dealing with health

    TODO : The rest of the TODOs
"""


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

        self.time_passed: float = 0
        self.current_connection: int = 0

        self.path_graph: List[Node] = self.world.paths[
            randint(0, len(self.world.paths) - 1)
        ]
        self.path: List[NodeRecord] = pathFindAStar(
            self.path_graph,
            self.path_graph.get_nearest_node(self.position),
            self.path_graph.nodes[self.base.target_node_index],
        )
        self.path_length: int = len(self.path)

        seeking_state: ArcherStateAttacking_TeamA = ArcherStateSeeking_TeamA(self)
        attacking_state: ArcherStateAttacking_TeamA = ArcherStateAttacking_TeamA(self)
        ko_state: ArcherStateKO_TeamA = ArcherStateKO_TeamA(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(ko_state)

        self.brain.set_state("seeking")

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

        # self.archer.path_graph: List[Node] = self.archer.world.paths[
        #     randint(0, len(self.archer.world.paths) - 1)
        # ]

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
            if self.archer.current_connection < self.archer.path_length:
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position
                self.archer.current_connection += 1
                print("seeking: +1 current_connection")

        return None

    def entry_actions(self) -> None:
        # nearest_node = self.archer.path_graph.get_nearest_node(self.archer.position)
        # self.archer.path = pathFindAStar(
        #     self.archer.path_graph,
        #     nearest_node,
        #     self.archer.path_graph.nodes[self.archer.base.target_node_index],
        # )

        # No need to set the graph two times (__init__ from Archer)
        # TODO : Utility method for setting path_graph?
        # self.archer.path = pathFindAStar(
        #     self.archer.path_graph,
        #     self.archer.path_graph.get_nearest_node(self.archer.position),
        #     self.archer.path_graph.nodes[self.archer.base.target_node_index],
        # )

        # self.archer.path_length: int = len(self.archer.path)
        # self.path_length = len(self.path)

        if self.archer.path_length > 0:
            # self.archer.current_connection = 0
            # self.archer.move_target.position = self.archer.path[0].fromNode.position
            self.archer.move_target.position = self.archer.path[self.archer.current_connection].fromNode.position
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

                if self.archer.current_connection < self.archer.path_length:
                    if (self.archer.position - self.archer.move_target.position).length() > 8:
                        self.archer.current_connection -= 1
                        self.archer.move_target.position = self.archer.path[
                            self.archer.current_connection
                        ].fromNode.position
                        self.archer.velocity = self.archer.move_target.position - self.archer.position
            else:
                # if can attack and not within range of the opponent, move towards
                # the opponent via the grid
                self.archer.velocity = self.archer.move_target.position - self.archer.position

                if self.archer.current_connection > 0:
                    if (self.archer.position - self.archer.move_target.position).length() < 8:
                        self.archer.current_connection += 1
                        self.archer.move_target.position = self.archer.path[
                            self.archer.current_connection
                        ].fromNode.position
                        self.archer.velocity = self.archer.move_target.position - self.archer.position
        # cannot attack
        else:
            if self.archer.current_connection < self.archer.path_length:
                if (self.archer.position - self.archer.move_target.position).length() < 8:
                    self.archer.current_connection -= 1
                    self.archer.move_target.position = self.archer.path[
                        self.archer.current_connection
                    ].fromNode.position
                    self.archer.velocity = self.archer.move_target.position - self.archer.position

        print("Archer move_target.position : ", self.archer.move_target.position)

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

            # self.archer.current_connection += 1
            # self.archer.move_target.position = self.archer.path[
            #     self.archer.current_connection
            # ].toNode.position
            return "seeking"

        return None

    def entry_actions(self) -> None:
        # self.archer.move_target.position = self.archer.path[0].fromNode.position
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
