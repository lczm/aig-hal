import pygame

from random import randint, random
from typing import List, Dict
from Graph import *
from Base import *

from Character import *
from State import *
from Utils_Mayasol import *

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

        self.levels: int = 0
        self.time_passed: float = 0
        self.current_connection: int = 0

        self.max_lane: Lane = 0

        self.path_graph: Graph = self.world.paths[
            randint(0, len(self.world.paths) - 1)
        ]
        # self.path: List[NodeRecord] = pathFindAStar(
        #     self.path_graph,
        #     self.path_graph.get_nearest_node(self.position),
        #     self.path_graph.nodes[self.base.target_node_index],
        # )
        self.path: List[Connection] = get_path_to_enemy_base(self, self.path_graph, self.position)
        self.path_length: int = len(self.path)

        self.on_base_kiting_path: bool = False
        self.path_base_kite_left: List[Connection] = self.get_path_base_kite_left()
        self.path_base_kite_right: List[Connection] = self.get_path_base_kite_right()

        seeking_state: ArcherStateAttacking_TeamA = ArcherStateSeeking_TeamA(self)
        attacking_state: ArcherStateAttacking_TeamA = ArcherStateAttacking_TeamA(self)
        fleeing_state: ArcherStateFleeing_TeamA = ArcherStateFleeing_TeamA(self)
        reposition_state: ArcherRepositionState_TeamA = ArcherRepositionState_TeamA(self)
        ko_state: ArcherStateKO_TeamA = ArcherStateKO_TeamA(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(fleeing_state)
        self.brain.add_state(reposition_state)
        self.brain.add_state(ko_state)

        self.brain.set_state("seeking")

    def get_path_base_kite_left(self) -> List[Connection]:
        connections: List[Connection] = []

        # furthest node, because when attacking, archer kites backwards
        startNode: Node = get_node_from_id(self.world.paths, 6)
        endNode: Node = get_node_from_id(self.world.paths, 5)
        connections.append(Connection(graph=self.path_graph, cost=0, fromNode=startNode, toNode=endNode))

        startNode = endNode
        endNode: Node = get_initial_start_node(self)
        connections.append(Connection(graph=self.path_graph, cost=0, fromNode=startNode, toNode=endNode))

        return connections

    def get_path_base_kite_right(self) -> List[Connection]:
        connections: List[Connection] = []

        # furthest node, because when attacking, archer kites backwards
        startNode: Node = get_node_from_id(self.world.paths, 2)
        endNode: Node = get_node_from_id(self.world.paths, 1)
        connections.append(Connection(graph=self.path_graph, cost=0, fromNode=startNode, toNode=endNode))

        startNode = endNode
        endNode: Node = get_initial_start_node(self)
        connections.append(Connection(graph=self.path_graph, cost=0, fromNode=startNode, toNode=endNode))

        return connections

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
            if self.levels < 2:
                self.level_up("speed")
            else:
                self.level_up("ranged damage")
                # self.level_up("ranged cooldown")
            self.levels += 1


class ArcherStateSeeking_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "seeking")
        self.archer: Archer_TeamA = archer

    def do_actions(self) -> None:
        # If using base kiting paths, reset them
        if self.archer.on_base_kiting_path and self.archer.current_connection == len(self.archer.path) - 1:
            if (self.archer.position - self.archer.move_target.position).length() < 8:
                # Reset current connection
                self.archer.current_connection = 0
                self.archer.path = get_path_to_enemy_base(self.archer, self.archer.path_graph, self.archer.position)
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position

                self.archer.on_base_kiting_path = False

        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self) -> str:
        if (self.archer.current_hp < (self.archer.max_hp / 100 * 50) and 
            self.archer.current_healing_cooldown <= 0):
            return "fleeing"

        if self.archer.on_base_kiting_path is False and (self.archer.position - self.archer.base.position).length() > 300:
            enemy_lanes: Dict[int, int] = get_enemies_positions_in_lanes(self.archer.world.paths, self.archer)
            current_lane: Lane = get_lane_character(self.archer.path_graph, self.archer)

            if current_lane != Lane.Base:
                max_enemies:int = 0
                max_lane:Lane = 0
                for key, value in enemy_lanes.items():
                    if value > max_enemies:
                        max_enemies = value
                        max_lane = key

                # If currently not at the lane with the most enemies
                if current_lane != max_lane:
                    self.archer.max_lane = max_lane
                    return "reposition"

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
            if self.archer.current_connection < len(self.archer.path) - 1:
                self.archer.current_connection += 1
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position
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

        if len(self.archer.path) > 0:
            # self.archer.current_connection = 0
            # self.archer.move_target.position = self.archer.path[0].fromNode.position
            self.archer.move_target.position = self.archer.path[self.archer.current_connection].toNode.position
        # else:
        #     self.archer.move_target.position = self.archer.path_graph.nodes[
        #         self.archer.base.target_node_index
        #     ].position
        return None


class ArcherStateAttacking_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "attacking")
        self.archer: Archer_TeamA = archer

    def do_actions(self):
        # TODO : Change target to the target that is closest to the archer
        # TODO : once changed, check surrounding radius by a certain amoutn
        # If enemy hp is (one-hit) status, change target to that

        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            if (self.archer.position - nearest_opponent.position).length() <= self.archer.min_target_distance:
                self.archer.target = nearest_opponent

        opponent_distance = (
            self.archer.position - self.archer.target.position
        ).length()

        # At the start of the path graph, node 0
        if (
            self.archer.on_base_kiting_path is False and
            self.archer.current_connection == 0 and
            (self.archer.position - self.archer.move_target.position).length() < 8 and
            opponent_distance <= self.archer.min_target_distance
        ):
            opponent_direction = self.archer.position - self.archer.target.position

            if self.archer.team_id == 0:
                if opponent_direction.y < 0: # If the opponent is below me, kite upwards
                    self.archer.path = self.archer.path_base_kite_right
                    print("Opponent is below me")
                else: # If the opponent is above me, kite downwards
                    self.archer.path = self.archer.path_base_kite_left
                    print("Opponent is above me")
            else:
                if opponent_direction.y > 0:
                    self.archer.path = self.archer.path_base_kite_left
                else:
                    self.archer.path = self.archer.path_base_kite_right
            
            self.archer.on_base_kiting_path = True
            self.archer.current_connection = len(self.archer.path) - 1
            self.archer.move_target.position = self.archer.path[
                self.archer.current_connection
            ].fromNode.position

        # if can attack
        if self.archer.current_ranged_cooldown <= 0:
            if opponent_distance <= self.archer.min_target_distance:
                self.archer.velocity = Vector2(0, 0)
                self.archer.ranged_attack(self.archer.target.position)

                if self.archer.current_connection > 0 and (self.archer.position - self.archer.move_target.position).length() < 8:
                    self.archer.current_connection -= 1
                    # print("### range attacked, current_connection - 1")

                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].fromNode.position
                self.archer.velocity = self.archer.move_target.position - self.archer.position

                # print("@@@ range attacked")
            else:
                # if can attack and not within range of the opponent, move towards
                # the opponent via the grid
                if self.archer.current_connection < len(self.archer.path) - 1 and (self.archer.position - self.archer.move_target.position).length() < 8:
                    self.archer.current_connection += 1
                    # print("### trying to range attack, current_connection + 1")
                
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position
                self.archer.velocity = self.archer.move_target.position - self.archer.position
                # print("@@@ trying to range attack")
        # cannot attack
        else:
            diff:Vector2 = self.archer.position - self.archer.path[self.archer.current_connection].fromNode.position
            if self.archer.current_connection > 0 and diff.x < 0 and diff.y < 0:
                self.archer.current_connection -= 1

            # if within the range of the opponent, run
            if self.archer.min_target_distance > opponent_distance:
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].fromNode.position
                self.archer.velocity = self.archer.move_target.position - self.archer.position

                if self.archer.current_connection > 0 and (self.archer.position - self.archer.move_target.position).length() < 8:
                    self.archer.current_connection -= 1
                    # print("### cannot attack, running from the range of the opponent - 1")

                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].fromNode.position
                self.archer.velocity = self.archer.move_target.position - self.archer.position
                # print("@@@ cannot attack, running from the range of the opponent")
                # print(f"fromNode: {self.archer.path[self.archer.current_connection].fromNode.position}")
                # print(f"toNode: {self.archer.path[self.archer.current_connection].toNode.position}")
                # print(f"current_connection: {self.archer.current_connection}")
            else:
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position
                if self.archer.current_connection > 0 and (self.archer.position - self.archer.move_target.position).length() < 8:
                    self.archer.current_connection -= 1
                    # print("### cannot attack, running towards the opponent - 1")

                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position

                self.archer.velocity = self.archer.move_target.position - self.archer.position
                # print("@@@ cannot attack, running towards the opponent")

        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self) -> str:
        # If less than 50% hp and can heal
        if (self.archer.current_hp < (self.archer.max_hp / 100 * 50) and 
            self.archer.current_healing_cooldown <= 0):
            return "fleeing"

        # target is gone
        if (
            self.archer.world.get(self.archer.target.id) is None
            or self.archer.target.ko
        ):
            self.archer.target = None
            if self.archer.on_base_kiting_path:
                # self.archer.current_connection = 0
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position
            else:
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].toNode.position
            self.archer.velocity = self.archer.move_target.position - self.archer.position
            return "seeking"
        
        # if the opponent is too far away from me
        opponent_distance = (
            self.archer.position - self.archer.target.position
        ).length()
        if opponent_distance > 200:
            self.archer.path = get_path_to_enemy_base(self.archer, self.archer.path_graph, self.archer.position)
            return "seeking"

        return None

    def entry_actions(self) -> None:
        # self.archer.move_target.position = self.archer.path[0].fromNode.position
        return None


class ArcherStateFleeing_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "fleeing")
        self.archer: Archer_TeamA = archer
    
    def do_actions(self) -> None:
        # Run back
        if self.archer.current_connection > 0 and (self.archer.position - self.archer.move_target.position).length() < 8:
            self.archer.current_connection -= 1

        self.archer.move_target.position = self.archer.path[
            self.archer.current_connection
        ].fromNode.position

        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

        # Heal, it will check if it can heal
        self.archer.heal()
        return None

    def check_conditions(self) -> str:
        if self.archer.current_hp > (self.archer.max_hp / 100 * 70):
            return "seeking"
        
        # If cant heal, there is no point in staying in the fleeing state, just
        # attack while it still can
        if self.archer.current_healing_cooldown > 0 and self.archer.target is not None:
            return "attacking"

        return None

    def entry_actions(self):
        return None


class ArcherRepositionState_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "reposition")
        self.archer: Archer_TeamA = archer
    
    def do_actions(self) -> None:
        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed
        return None

    def check_conditions(self) -> str:
        # If there is an enemy nearby while trying to reposition, just attack the enemy
        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            if (self.archer.position - nearest_opponent.position).length() <= self.archer.min_target_distance:
                self.archer.target = nearest_opponent
                return "attacking"

        if self.archer.current_connection == 0 and (self.archer.position - self.archer.move_target.position).length() < 8:
            self.archer.path_graph = get_graph(self.archer, self.archer.max_lane)
            self.archer.path = get_path_to_enemy_base(self.archer, self.archer.path_graph, self.archer.position)
            return "seeking"

        if (self.archer.position - self.archer.move_target.position).length() < 8:
            # continue on path
            if self.archer.current_connection > 0:
                self.archer.current_connection -= 1
                self.archer.move_target.position = self.archer.path[
                    self.archer.current_connection
                ].fromNode.position
        return None

    def entry_actions(self) -> None:
        # Upon entering into reposition state, move to the nearest max_lane node
        # self.archer.path: List[NodeRecord] = get_path_to_my_base(self.archer, self.archer.path_graph, self.archer.position)
        self.archer.move_target.position = self.archer.path[
            self.archer.current_connection
        ].fromNode.position
        return None

class ArcherStateKO_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "ko")
        self.archer: Archer_TeamA = archer

    def do_actions(self) -> None:
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
        self.archer.current_connection = 0
        return None
