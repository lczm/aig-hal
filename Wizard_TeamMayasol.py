import pygame

from random import randint, random
from Graph import *
from typing import List, Dict

from Character import *
from State import *
from Utils_Mayasol import *


class Wizard_TeamMayasol(Character):

    def __init__(self, world, image, projectile_image, base, position, explosion_image=None):

        Character.__init__(self, world, "wizard", image)

        self.projectile_image = projectile_image
        self.explosion_image = explosion_image

        self.base: Base = base
        self.position: Vector2 = position
        self.move_target: GameEntity = GameEntity(
            world, "wizard_move_target", None)
        self.target: GameEntity = None
        self.level: int = 0
        self.current_connection: int = 0
        self.paths = generate_pathfinding_graphs(
            "pathfinding_mayasol.txt", self)
        self.path_graph: Graph = self.paths[1]
        self.path: List[Connection] = get_path_to_enemy_base(
            self, self.path_graph, self.position)
        self.supporting_knight: bool = True
        self.safe_distance: int = 250
        self.time_passed: float = 0
        self.danger_radius = 700

        self.maxSpeed: int = 50
        self.min_target_distance: int = 100
        self.projectile_range: int = 100
        self.projectile_speed: int = 100

        seeking_state: WizardStateSeeking_TeamMayasol = WizardStateSeeking_TeamMayasol(
            self)
        attacking_state: WizardStateAttacking_TeamMayasol = WizardStateAttacking_TeamMayasol(
            self)
        defending_state: WizardStateDefending_TeamMayasol = WizardStateDefending_TeamMayasol(
            self)
        ko_state: WizardStateKO_TeamMayasol = WizardStateKO_TeamMayasol(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(defending_state)
        self.brain.add_state(ko_state)

        self.brain.set_state("seeking")

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

    def defend(self) -> bool:
        enemy_lane_scores = get_amount_of_enemies_in_range_by_score(
            self.base, self.paths, self.danger_radius)
        for lane in enemy_lane_scores:
            # knight(4) + archer(4) + wizard(6)
            if enemy_lane_scores[lane] >= 11:
                return True

        return False

    def within_danger_radius(self) -> bool:
        if (self.position - self.path_graph.nodes[self.base.spawn_node_index].position).length() < self.danger_radius:
            return True
        return False

    def close_to_base(self) -> bool:
        if (self.position - self.path_graph.nodes[self.base.spawn_node_index].position).length() < 40:
            return True
        return False

    def at_start_of_connection(self) -> bool:
        if self.current_connection == 0:
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
        projectile_explode_time: float = distance_from_target.length() / \
            self.projectile_speed
        predicted_point: Vector2 = self.target.position + \
            (self.target.velocity * projectile_explode_time)
        return predicted_point

    def predict_enemy_location(self, enemy: Character) -> Vector2:
        distance_from_target: Vector2 = self.position - enemy.position
        projectile_explode_time: float = distance_from_target.length() / \
            self.projectile_speed
        predicted_point: Vector2 = enemy.position + \
            (enemy.velocity * projectile_explode_time)
        return predicted_point

    def predict_maximum_damage_area(self) -> Vector2:
        enemy_list: List[Character] = get_enemies_in_range(
            self, self.projectile_range)
        predicted_positions: List[Vector2] = []

        for entity in enemy_list:
            predicted_point = self.predict_enemy_location(entity)
            predicted_positions.append(predicted_point)

        for i in range(len(enemy_list)):
            for j in range(len(enemy_list)):
                # 96 as rect of explosion is that size
                if (predicted_positions[i] - predicted_positions[j]).length() <= 96:
                    x = (predicted_positions[i].x +
                         predicted_positions[j].x) / 2
                    y = (predicted_positions[i].y +
                         predicted_positions[j].y) / 2
                    maximum_damage_point = Vector2(x, y)
                    return maximum_damage_point

        return self.predict_target_location()

    def grouped_with_knight(self) -> bool:
        knight_lane: Lane
        entity: Character

        # check knight's lane
        for entity in self.world.entities.values():
            if entity.team_id != self.team_id:
                continue
            if entity.name != "knight":
                continue
            if entity.ko:
                continue

            knight_lane = get_lane_character(entity.path_graph, entity)
            wizard_lane = get_lane_character(
                self.path_graph, self)

            if (knight_lane == wizard_lane):
                return True

        return False

    def find_knight_lane_graph(self) -> Graph:
        knight_lane: Lane
        entity: Character

        # return knight's graph if knight exists
        for entity in self.world.entities.values():
            if entity.team_id != self.team_id:
                continue
            if entity.name != "knight":
                continue
            if entity.ko:
                continue

            knight_lane = get_lane_character(entity.path_graph, entity)
            return get_graph(entity, entity.path_graph, knight_lane)

        # go bot if no knight
        return self.paths[1]

    def find_knight_lane(self) -> Lane:
        knight_lane: Lane
        entity: Character

        for entity in self.world.entities.values():
            if entity.team_id != self.team_id:
                continue
            if entity.name != "knight":
                continue
            if entity.ko:
                continue

            knight_lane = get_lane_character(entity.path_graph, entity)
            return knight_lane

        return get_lane_character(self.path_graph, self)

    def render(self, surface):
        Character.render(self, surface)
        # for i in range(0, len(self.path) - 1):
        #    from_position: Vector2 = self.path[i].fromNode.position
        #    to_position: Vector2 = self.path[i].toNode.position

        #    draw_circle_at_position(from_position, surface, (0, 255, 0))
        #    draw_circle_at_position(to_position, surface, (0, 255, 0))

        #from_position: Vector2 = self.path[self.current_connection].fromNode.position
        #to_position: Vector2 = self.path[self.current_connection].toNode.position

        #draw_circle_at_position(from_position, surface, (0, 0, 255))
        #draw_circle_at_position(to_position, surface, (255, 0, 0))

    def process(self, time_passed):

        Character.process(self, time_passed)
        self.time_passed = time_passed

        if self.can_level_up():
            if (self.level < 1):
                self.level_up("speed")
            else:
                self.level_up("ranged cooldown")
            self.level += 1


class WizardStateSeeking_TeamMayasol(State):

    def __init__(self, wizard):

        State.__init__(self, "seeking")
        self.wizard: Wizard_TeamMayasol = wizard

    def do_actions(self):

        # if not attacking and not max hp, heal
        if (self.wizard.current_hp != self.wizard.max_hp):
            self.wizard.heal()

        self.wizard.velocity = self.wizard.move_target.position - self.wizard.position
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip()
            self.wizard.velocity *= self.wizard.maxSpeed
        dodge_projectile(self.wizard)

    def check_conditions(self):

        if self.wizard.target.__class__.__name__ == "base":
            return None

        if self.wizard.defend() and not self.wizard.within_danger_radius():
            self.wizard.path_graph = get_graph(self.wizard,
                                               self.wizard.path_graph,
                                               get_lane(get_nearest_node_global_ignoring_base(
                                                   self.wizard.paths, self.wizard.position).id))
            self.wizard.path = get_path_from_base_to_position(
                self.wizard, self.wizard.path_graph)
            self.wizard.current_connection = len(self.wizard.path) - 1
            return "defending"

        # check if opponent is in range
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position -
                                 nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                self.wizard.target = nearest_opponent
                return "attacking"

        if (self.wizard.position - self.wizard.move_target.position).length() < 8:

            # continue on path
            if self.wizard.connection_not_at_end():
                self.wizard.increment_connection()
                self.wizard.move_target.position = self.wizard.path[
                    self.wizard.current_connection].toNode.position

        return None

    def entry_actions(self):
        if len(self.wizard.path) > 0 and self.wizard.current_connection <= len(self.wizard.path) - 1:
            self.wizard.move_target.position = self.wizard.path[
                self.wizard.current_connection].toNode.position


class WizardStateAttacking_TeamMayasol(State):

    def __init__(self, wizard):

        State.__init__(self, "attacking")
        self.wizard: Wizard_TeamMayasol = wizard

    def do_actions(self):

        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        # dont switch target if attacking base
        if nearest_opponent is not None and not self.wizard.target.__class__.__name__ == "base":
            # Set target to nearest opponent
            if (self.wizard.position - nearest_opponent.position).length() <= self.wizard.min_target_distance:
                self.wizard.target = nearest_opponent

        opponent_distance = (self.wizard.position -
                             self.wizard.target.position).length()

        if self.wizard.can_attack():
            if self.wizard.within_attack_range(opponent_distance):
                self.wizard.velocity = Vector2(0, 0)
                self.wizard.ranged_attack(
                    self.wizard.predict_maximum_damage_area(), self.wizard.explosion_image)

                if self.wizard.at_node() and self.wizard.connection_not_at_start():
                    self.wizard.decrement_connection()

                self.wizard.set_move_target_from_node()
                self.wizard.set_velocity()
            else:
                if self.wizard.at_node() and self.wizard.connection_not_at_end():
                    self.wizard.increment_connection()

                self.wizard.set_move_target_to_node()
                self.wizard.set_velocity()
        else:
            # if within the range of the opponent, run
            if self.wizard.min_target_distance > opponent_distance:
                self.wizard.set_move_target_from_node()

                if self.wizard.connection_not_at_start() and self.wizard.at_node():
                    self.wizard.decrement_connection()
                self.wizard.set_move_target_from_node()
            else:
                self.wizard.set_move_target_to_node()

                if self.wizard.connection_not_at_start() and self.wizard.at_node():
                    self.wizard.decrement_connection()
                self.wizard.set_move_target_to_node()

        self.wizard.set_velocity()
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip()
            self.wizard.velocity *= self.wizard.maxSpeed

        dodge_projectile(self.wizard)

    def check_conditions(self):
        if self.wizard.defend() and not self.wizard.within_danger_radius():
            self.wizard.path_graph = get_graph(self.wizard,
                                               self.wizard.path_graph,
                                               get_lane(get_nearest_node_global_ignoring_base(
                                                   self.wizard.paths, self.wizard.position).id))
            self.wizard.path = get_path_from_base_to_position(
                self.wizard, self.wizard.path_graph)
            self.wizard.current_connection = len(self.wizard.path) - 1
            return "defending"

        # if the opponent is too far
        opponent_distance = (
            self.wizard.position - self.wizard.target.position
        ).length()
        if opponent_distance > 200:
            return "seeking"

        if self.wizard.world.get(self.wizard.target.id) is None or self.wizard.target.ko:
            self.wizard.target = None
            return "seeking"

        return None

    def entry_actions(self):

        return None


class WizardStateDefending_TeamMayasol(State):
    def __init__(self, wizard):

        State.__init__(self, "defending")
        self.wizard = wizard

    def do_actions(self):
        if (self.wizard.current_hp != self.wizard.max_hp):
            self.wizard.heal()
        self.wizard.set_move_target_from_node()
        if self.wizard.connection_not_at_start() and self.wizard.at_node():
            self.wizard.decrement_connection()
            self.wizard.set_move_target_from_node()

        self.wizard.set_velocity()
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip()
            self.wizard.velocity *= self.wizard.maxSpeed
        dodge_projectile(self.wizard, False, False, False)
        return None

    def check_conditions(self):
        if not self.wizard.defend():
            self.wizard.path_graph = get_bot_graph(self.wizard)
            self.wizard.path = get_path_to_enemy_base_from_my_base(
                self.wizard, self.wizard.path_graph)
            return "seeking"
        elif self.wizard.within_danger_radius() and self.wizard.close_to_base():
            nearest_opponent = self.wizard.world.get_nearest_opponent(
                self.wizard)
            if nearest_opponent is not None:
                opponent_distance = (self.wizard.position -
                                     nearest_opponent.position).length()
                if opponent_distance <= self.wizard.min_target_distance:
                    self.wizard.target = nearest_opponent
                    self.wizard.path = get_path_to_enemy_base_from_my_base(
                        self.wizard, self.wizard.path_graph)
                    return "attacking"

    def entry_actions(self):

        return None


class WizardStateKO_TeamMayasol(State):

    def __init__(self, wizard):

        State.__init__(self, "ko")
        self.wizard = wizard

    def do_actions(self):

        return None

    def check_conditions(self):

        # respawned
        if self.wizard.current_respawn_time <= 0:
            self.wizard.current_respawn_time = self.wizard.respawn_time
            self.wizard.ko = False
            # follow knight when respawned
            self.wizard.path_graph = self.wizard.paths[1]
            # self.wizard.path = get_path_to_enemy_base(
            #    self.wizard, self.wizard.path_graph, self.wizard.position)
            self.wizard.path = get_path_to_enemy_base_from_my_base(
                self.wizard, self.wizard.path_graph)
            return "seeking"

        return None

    def entry_actions(self):

        self.wizard.current_hp = self.wizard.max_hp
        self.wizard.position = Vector2(self.wizard.base.spawn_position)
        self.wizard.velocity = Vector2(0, 0)
        self.wizard.target = None
        self.wizard.current_connection = 0

        return None
