import pygame

from random import randint, random
from Graph import *
from typing import List, Dict

from Character import *
from State import *
from Utils_Mayasol import *


class Wizard_TeamA(Character):

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
        self.path_graph: Graph = self.world.paths[
            randint(0, len(self.world.paths) - 1)
        ]
        self.path: List[Connection] = get_path_to_enemy_base(
            self, self.path_graph, self.position)
        self.supporting_knight: bool = True
        self.safe_distance: int = 250
        self.time_passed: float = 0

        self.maxSpeed: int = 50
        self.min_target_distance: int = 100
        self.projectile_range: int = 100
        self.projectile_speed: int = 100

        seeking_state: WizardStateSeeking_TeamA = WizardStateSeeking_TeamA(
            self)
        attacking_state: WizardStateAttacking_TeamA = WizardStateAttacking_TeamA(
            self)
        ko_state: WizardStateKO_TeamA = WizardStateKO_TeamA(self)
        fleeing_state: WizardStateFleeing_TeamA = WizardStateFleeing_TeamA(
            self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(fleeing_state)
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
            print("kngiht lane" + str(knight_lane))
            return get_graph(entity, entity.path_graph, knight_lane)

        print("using random graph")
        # go bot if no knight
        return self.world.paths[2]

    def render(self, surface):

        Character.render(self, surface)

    def process(self, time_passed):

        Character.process(self, time_passed)
        self.time_passed = time_passed

        level_up_stats: typing.List[str] = [
            "hp", "speed", "ranged damage", "ranged cooldown", "projectile range"]
        if self.can_level_up():
            self.level_up("speed")
            # if (self.level < 2):
            #    self.level_up("speed")
            # else:
            #    # TODO: check if ranged damange > ranged cooldown
            #    self.level_up("ranged damage")
            self.level += 1


class WizardStateSeeking_TeamA(State):

    def __init__(self, wizard):

        State.__init__(self, "seeking")
        self.wizard: Wizard_TeamA = wizard
        # follow knight on startup
        self.wizard.path_graph = self.wizard.find_knight_lane_graph()
        self.wizard.path = get_path_to_enemy_base(
            self.wizard, self.wizard.path_graph, self.wizard.position)

    def do_actions(self):

        self.wizard.velocity = self.wizard.move_target.position - self.wizard.position
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip()
            self.wizard.velocity *= self.wizard.maxSpeed
        dodge_projectile(self.wizard)

    def check_conditions(self):
        if (self.wizard.current_hp < (self.wizard.max_hp / 100 * 50) and
                self.wizard.can_heal()):
            return "fleeing"

        # check if opponent is in range
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position -
                                 nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                self.wizard.target = nearest_opponent
                return "attacking"

        # group up with knight if not already grouped
        # if not self.wizard.grouped_with_knight():
        #    print("not grouped with knight")
        #    self.wizard.path_graph = self.wizard.find_knight_lane_graph()
        #    self.wizard.path = get_path_to_enemy_base(
        #        self.wizard, self.wizard.path_graph, self.wizard.position)
        #    self.wizard.current_connection = 0

        if (self.wizard.position - self.wizard.move_target.position).length() < 8:

            # continue on path
            if self.wizard.current_connection < len(self.wizard.path) - 1:
                self.wizard.increment_connection()
                self.wizard.move_target.position = self.wizard.path[
                    self.wizard.current_connection].toNode.position

        return None

    def entry_actions(self):
        if len(self.wizard.path) > 0 and self.wizard.current_connection <= len(self.wizard.path) - 1:
            self.wizard.move_target.position = self.wizard.path[
                self.wizard.current_connection].toNode.position

        # nearest_node = self.wizard.path_graph.get_nearest_node(
            # self.wizard.position)

        # self.path = pathFindAStar(self.wizard.path_graph,
            # nearest_node,
            # self.wizard.path_graph.nodes[self.wizard.base.target_node_index])

        #self.path_length = len(self.path)

        # if (self.path_length > 0):
            #self.current_connection = 0
            #self.wizard.move_target.position = self.path[0].fromNode.position

        # else:
            # self.wizard.move_target.position = self.wizard.path_graph.nodes[
            # self.wizard.base.target_node_index].position


class WizardStateAttacking_TeamA(State):

    def __init__(self, wizard):

        State.__init__(self, "attacking")
        self.wizard: Wizard_TeamA = wizard

    def do_actions(self):

        # Set target to nearest opponent
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            if (self.wizard.position - nearest_opponent.position).length() <= self.wizard.min_target_distance:
                self.wizard.target = nearest_opponent

        opponent_distance = (self.wizard.position -
                             self.wizard.target.position).length()

        if self.wizard.can_attack():
            if self.wizard.within_attack_range(opponent_distance):
                self.wizard.velocity = Vector2(0, 0)
                self.wizard.ranged_attack(
                    self.wizard.predict_target_location(), self.wizard.explosion_image)

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

            # dodge projectiles
           # nearest_projectile = get_nearest_projectile(self.wizard)
           # if nearest_projectile is not None:
           #     projectile_distance = (self.wizard.position -
           #                            nearest_projectile.position).length()
           #     if projectile_distance <= self.wizard.min_target_distance:

        self.wizard.set_velocity()
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip()
            self.wizard.velocity *= self.wizard.maxSpeed

        dodge_projectile(self.wizard)

    def check_conditions(self):
        if (self.wizard.current_hp < (self.wizard.max_hp / 100 * 50) and
                self.wizard.can_heal()):
            return "fleeing"
        # target is gone
        if self.wizard.world.get(self.wizard.target.id) is None or self.wizard.target.ko:
            self.wizard.target = None
            return "seeking"

        return None

    def entry_actions(self):

        return None


class WizardStateFleeing_TeamA(State):
    def __init__(self, wizard):

        State.__init__(self, "fleeing")
        self.wizard = wizard

    def do_actions(self) -> None:
        if self.wizard.connection_not_at_start() and self.wizard.at_node():
            self.wizard.decrement_connection()

        self.wizard.set_move_target_from_node()
        self.wizard.set_velocity()
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip()
            self.wizard.velocity *= self.wizard.maxSpeed
        self.wizard.heal()
        return None

    def check_conditions(self) -> str:
        if self.wizard.current_hp > (self.wizard.max_hp / 100 * 70):
            return "seeking"

        # check if any opponent in the safe distance
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position -
                                 nearest_opponent.position).length()
            if opponent_distance >= self.wizard.safe_distance:
                return "seeking"

        if not self.wizard.can_heal() and self.wizard.has_target():
            return "attacking"

        return None

    def entry_actions(self) -> None:
        return None


class WizardStateKO_TeamA(State):

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
            self.wizard.path_graph = self.wizard.find_knight_lane_graph()
            self.wizard.path = get_path_to_enemy_base(
                self.wizard, self.wizard.path_graph, self.wizard.position)
            return "seeking"

        return None

    def entry_actions(self):

        self.wizard.current_hp = self.wizard.max_hp
        self.wizard.position = Vector2(self.wizard.base.spawn_position)
        self.wizard.velocity = Vector2(0, 0)
        self.wizard.target = None
        self.wizard.current_connection = 0

        return None
