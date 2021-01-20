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

        self.paths: List[Graph] = generate_pathfinding_graphs("more_pathfinding_nodes.txt", self)
        self.path_graph: Graph = self.paths[0]
        # self.path_graph: Graph = self.world.paths[
        #     randint(0, len(self.world.paths) - 1)
        # ]

        self.path: List[Connection] = get_path_to_enemy_base(self, self.path_graph, self.position)

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
        connections = generate_series_of_connections(self, [6, 24, 23, 22, 5, 
                                                     get_initial_start_node(self).id])
        return connections

    def get_path_base_kite_right(self) -> List[Connection]:
        connections = generate_series_of_connections(self, [2, 17, 16, 15, 14, 1,
                                                     get_initial_start_node(self).id])
        return connections

    def set_move_target_from_node(self) -> None:
        self.move_target.position = self.path[self.current_connection].fromNode.position
        return None

    def set_move_target_to_node(self) -> None:
        self.move_target.position = self.path[self.current_connection].toNode.position
        return None

    def at_node(self) -> bool:
        # 8 is the rough estimate that is acceptable for being considered
        # 'at the node'
        if (self.position - self.move_target.position).length() < 8:
            return True
        return False
    
    def increment_connection(self) -> None:
        if self.current_connection < len(self.path) - 1:
            self.current_connection += 1
        return None
        
    def decrement_connection(self) -> None:
        if self.current_connection > 0:
            self.current_connection -= 1
        return None
    
    def at_start_of_connection(self) -> bool:
        if self.current_connection == 0:
            return True
        return False

    def at_end_of_connection(self) -> bool:
        if self.current_connection == len(self.path) - 1:
            return True
        return False

    def connection_not_at_start(self) -> bool:
        if self.current_connection > 0:
            return True
        return False
    
    def connection_not_at_end(self) -> bool:
        if self.current_connection < len(self.path) - 1:
            return True
        return False

    def set_current_connection_to_min(self) -> None:
        self.current_connection = 0
        return None

    def set_current_connection_to_max(self) -> None:
        self.current_connection = len(self.path) - 1
        return None

    def can_attack(self) -> bool:
        if self.current_ranged_cooldown <= 0:
            return True
        return False
    
    def can_heal(self) -> bool:
        if self.current_healing_cooldown <= 0:
            return True
        return False
    
    def within_attack_range(self, opponent_distance: float) -> bool:
        if opponent_distance <= self.min_target_distance:
            return True
        return False

    def set_velocity(self) -> None:
        self.velocity = self.move_target.position - self.position
        return None

    def has_target(self) -> bool:
        if self.target is not None:
            return True
        return False

    def predict_target_location(self) -> Vector2:
        distance_from_target: Vector2 = self.position - self.target.position
        projectile_time: float = distance_from_target.length() / self.projectile_speed
        predicted_point: Vector2 = self.target.position + (self.target.velocity * projectile_time)
        return predicted_point
    
    def render(self, surface) -> None:
        Character.render(self, surface)

        from_position: Vector2 = self.path[self.current_connection].fromNode.position
        to_position: Vector2 = self.path[self.current_connection].toNode.position

        draw_circle_at_position(from_position, surface, (0, 0, 255))
        draw_circle_at_position(to_position, surface, (255, 0, 0))

        return None

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
            if self.levels < 3:
                self.level_up("speed")
            else:
                if self.levels % 2 == 0:
                    self.level_up("ranged damage")
                else:
                    self.level_up("ranged cooldown")
            self.levels += 1


class ArcherStateSeeking_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "seeking")
        self.archer: Archer_TeamA = archer

    def do_actions(self) -> None:
        # If using base kiting paths, reset them
        if self.archer.on_base_kiting_path and self.archer.at_end_of_connection():
            if self.archer.at_node():
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

        if (self.archer.on_base_kiting_path is False and
            (self.archer.position - self.archer.base.position).length() > 400):
            highest_threat_lane = get_highest_lane_threat(self.archer.paths, self.archer)
            current_lane: Lane = get_lane_character(self.archer.path_graph, self.archer)

            if current_lane != highest_threat_lane:
                self.archer.max_lane = highest_threat_lane
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
            if self.archer.connection_not_at_end():
                self.archer.increment_connection()
                self.archer.set_move_target_to_node()
                print("seeking: +1 current_connection")

        return None

    def entry_actions(self) -> None:
        if len(self.archer.path) > 0 and self.archer.current_connection <= len(self.archer.path) - 1:
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
        # TODO : once changed, check surrounding radius by a certain amount
        # If enemy hp is (one-hit) status, change target to that

        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            if (self.archer.position - nearest_opponent.position).length() <= self.archer.min_target_distance:
                # If the new opponent found is not the same and 
                # If on kiting path, set back to normal path
                if nearest_opponent != self.archer.target and self.archer.on_base_kiting_path:
                    self.archer.path = get_path_to_enemy_base_from_my_base(self.archer, self.archer.path_graph)
                    self.archer.current_connection = 0
                    self.archer.on_base_kiting_path = False
                # Set the target for the archer
                self.archer.target = nearest_opponent

        opponent_distance = (
            self.archer.position - self.archer.target.position
        ).length()

        # if (self.archer.on_base_kiting_path and
        #     self.archer.at_end_of_connection() and
        #     self.archer.at_node()):
        #     self.archer.path = self.archer.path.reverse()

        # At the start of the path graph, node 0
        if (
            self.archer.on_base_kiting_path is False and
            self.archer.at_start_of_connection() and 
            self.archer.at_node() and 
            opponent_distance <= self.archer.min_target_distance
        ):
            opponent_direction = self.archer.position - self.archer.target.position

            # Change kiting path depending on which team and location the enemy is
            if self.archer.team_id == 0:
                if opponent_direction.y < 0: # If the opponent is below me, kite upwards
                    self.archer.path = self.archer.path_base_kite_right
                else: # If the opponent is above me, kite downwards
                    self.archer.path = self.archer.path_base_kite_left
            else:
                if opponent_direction.y > 0:
                    self.archer.path = self.archer.path_base_kite_left
                else:
                    self.archer.path = self.archer.path_base_kite_right
            
            self.archer.on_base_kiting_path = True
            self.archer.set_current_connection_to_max()
            self.archer.set_move_target_from_node()

        # if can attack
        if self.archer.can_attack():
            if self.archer.within_attack_range(opponent_distance):
                self.archer.velocity = Vector2(0, 0)
                # self.archer.ranged_attack(self.archer.target.position)
                self.archer.ranged_attack(self.archer.predict_target_location())

                if self.archer.at_node() and self.archer.connection_not_at_start(): 
                    self.archer.decrement_connection()

                self.archer.set_move_target_from_node()
                self.archer.set_velocity()
            else:
                # if can attack and not within range of the opponent, move towards
                # the opponent via the grid
                if self.archer.at_node() and self.archer.connection_not_at_end(): 
                    self.archer.increment_connection()
                
                self.archer.set_move_target_to_node()
                self.archer.set_velocity()
        # cannot attack
        else:
            # if within the range of the opponent, run
            if self.archer.min_target_distance > opponent_distance:
                self.archer.set_move_target_from_node()

                if self.archer.connection_not_at_start() and self.archer.at_node(): 
                    self.archer.decrement_connection()
                self.archer.set_move_target_from_node()
            else:
                self.archer.set_move_target_to_node()

                if self.archer.connection_not_at_start() and self.archer.at_node(): 
                    # self.archer.decrement_connection()
                    self.archer.increment_connection()
                self.archer.set_move_target_to_node()

        self.archer.set_velocity()
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self) -> str:
        # If less than 50% hp and can heal
        if (self.archer.current_hp < (self.archer.max_hp / 100 * 50) and 
            self.archer.can_heal()):
            return "fleeing"

        # target is gone
        if (
            self.archer.world.get(self.archer.target.id) is None
            or self.archer.target.ko
        ):
            self.archer.target = None
            # self.archer.set_move_target_to_node()
            # self.archer.velocity = self.archer.move_target.position - self.archer.position
            return "seeking"
        
        # if the opponent is too far away from me
        opponent_distance = (
            self.archer.position - self.archer.target.position
        ).length()
        if opponent_distance > 200:
            self.archer.path = get_path_to_enemy_base(self.archer, self.archer.path_graph, self.archer.position)
            print("Setting self.archer.path to get_path_enemy_base()")
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
        # if self.archer.at_start_of_connection() and self.archer.at_node():
        #     self.archer.decrement_connection

        # if self.archer.on_base_kiting_path:
        #     if self.archer.connection_not_at_end() and self.archer.at_node():
        #         self.archer.increment_connection()
        #     self.archer.set_move_target_to_node()
        # else:

        if self.archer.connection_not_at_start() and self.archer.at_node(): 
            self.archer.decrement_connection()
        self.archer.set_move_target_from_node()

        self.archer.set_velocity()
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
        if not self.archer.can_heal() and self.archer.has_target():
            return "attacking"

        return None

    def entry_actions(self):
        return None


class ArcherRepositionState_TeamA(State):
    def __init__(self, archer):
        State.__init__(self, "reposition")
        self.archer: Archer_TeamA = archer
    
    def do_actions(self) -> None:
        self.archer.set_velocity()
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

        # If at the start of the path, get a new path and go back to seeking
        if self.archer.at_start_of_connection() and self.archer.at_node():
            self.archer.path_graph = get_graph(self.archer, self.archer.path_graph, self.archer.max_lane)
            self.archer.path = get_path_to_enemy_base(self.archer, self.archer.path_graph, self.archer.position)
            return "seeking"

        # otherwise, continue on path
        if self.archer.connection_not_at_start() and self.archer.at_node():
            self.archer.decrement_connection()
            self.archer.set_move_target_from_node()
        return None

    def entry_actions(self) -> None:
        # Upon entering into reposition state, move to the nearest max_lane node
        # self.archer.path: List[NodeRecord] = get_path_to_my_base(self.archer, self.archer.path_graph, self.archer.position)
        self.archer.set_move_target_from_node()
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
            # self.archer.path_graph = self.archer.world.paths[
            #     randint(0, len(self.archer.world.paths) - 1)
            # ]
            self.archer.path_graph = self.archer.paths[
                randint(0, len(self.archer.paths) - 1)
            ]
            self.archer.path: List[Connection] = get_path_to_enemy_base(self.archer, self.archer.path_graph, self.archer.position)
            self.archer.current_connection = 0
            return "seeking"
        return None

    def entry_actions(self):
        self.archer.current_hp = self.archer.max_hp
        self.archer.position = Vector2(self.archer.base.spawn_position)
        self.archer.velocity = Vector2(0, 0)
        self.archer.target = None
        return None
