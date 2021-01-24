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
        self.xp = 2000

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
        # return a random graph if there is no knight
        return self.world.paths[1]

    def dodge_projectile(self):
        nearest_projectile: GameEntity = get_nearest_projectile(self)
        if nearest_projectile is not None:
            distance_from_origin: Vector2 = nearest_projectile.position - \
                nearest_projectile.origin_position
            distance_until_despawn: float = nearest_projectile.max_range - \
                distance_from_origin.length()
            original_velocity: Vector2 = nearest_projectile.velocity / nearest_projectile.maxSpeed
            # normal projectile
            if not nearest_projectile.explosive_image:
                for i in range(int(distance_until_despawn)):
                    projectile_rect: Rect = nearest_projectile.rect
                    w, h = nearest_projectile.image.get_size()
                    projectile_rect.x = nearest_projectile.position.x + \
                        (original_velocity.x * i) - w/2
                    projectile_rect.y = nearest_projectile.position.y + \
                        (original_velocity.y * i) - h/2
                    if (self.rect.colliderect(projectile_rect)):
                        distance_until_collide: float = nearest_projectile.position.length(
                        ) - Vector2(projectile_rect.left, projectile_rect.top).length()
                        # rotate velocity 90 degree clockwise from projectile
                        projectile_velocity = Vector2(
                            nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                        y_velocity = projectile_velocity.y
                        projectile_velocity.x *= -1
                        projectile_velocity.y = projectile_velocity.x
                        projectile_velocity.x = y_velocity
                        fake_velocity = Vector2(
                            projectile_velocity.x, projectile_velocity.y)
                        fake_rect = self.rect.copy()
                        character_original_velocity = fake_velocity / self.maxSpeed

                        for j in range(int(distance_until_collide + 1)):
                            fake_rect.x = self.position.x + \
                                (character_original_velocity.x * j)
                            fake_rect.y = self.position.y + \
                                (character_original_velocity.y * j)
                            fake_rect_position = Vector2(
                                fake_rect.x, fake_rect.y)
                            # if possible to dodge
                            if not (projectile_rect.colliderect(fake_rect)) \
                                    and not check_for_obstacles(fake_rect, self.world.obstacles) \
                                    and not check_screen_edge(fake_rect_position):
                                # dodge 90 degree clockwise from the projectile
                                #self.velocity.x *= -1
                                #self.velocity.y = self.velocity.x
                                #self.velocity.x = y_velocity
                                self.velocity = fake_rect_position - self.position
                                self.velocity.normalize_ip()
                                self.velocity *= self.maxSpeed
                                return

                        # if code reaches here means cant dodge 90 degree clockwise
                        projectile_velocity = Vector2(
                            nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                        x_velocity = projectile_velocity.x
                        projectile_velocity.y *= -1
                        projectile_velocity.x = projectile_velocity.y
                        projectile_velocity.y = x_velocity
                        fake_velocity = Vector2(
                            projectile_velocity.x, projectile_velocity.y)
                        fake_rect = self.rect.copy()
                        character_original_velocity = fake_velocity / self.maxSpeed
                        for j in range(int(distance_until_collide + 1)):
                            fake_rect.x = self.position.x + \
                                (character_original_velocity.x * j)
                            fake_rect.y = self.position.y + \
                                (character_original_velocity.y * j)
                            fake_rect_position = Vector2(
                                fake_rect.x, fake_rect.y)
                            # if possible to dodge
                            if not (projectile_rect.colliderect(fake_rect)) \
                                    and not check_for_obstacles(fake_rect, self.world.obstacles) \
                                    and not check_screen_edge(fake_rect_position):
                                # dodge 90 degree counterclockwise from the projectile
                                self.velocity = fake_rect_position - self.position
                                self.velocity.normalize_ip()
                                self.velocity *= self.maxSpeed
                                return

                        # check if can dodge 180 degrees backward
                        projectile_velocity = Vector2(
                            nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                        x_velocity = projectile_velocity.x
                        projectile_velocity.y *= -1
                        projectile_velocity.x *= -1
                        fake_velocity = Vector2(
                            projectile_velocity.x, projectile_velocity.y)
                        fake_rect = self.rect.copy()
                        character_original_velocity = fake_velocity / self.maxSpeed
                        #x_velocity = fake_character.velocity.x
                        #fake_character.velocity.y *= -1
                        #fake_character.velocity.x = fake_character.velocity.y
                        #fake_character.velocity.y = x_velocity
                        for k in range(int(distance_until_collide + 1)):
                            fake_rect.x = self.position.x + \
                                (character_original_velocity.x * k)
                            fake_rect.y = self.position.y + \
                                (character_original_velocity.y * k)
                            fake_rect_position = Vector2(
                                fake_rect.x, fake_rect.y)
                            # if possible to dodge
                            if not (projectile_rect.colliderect(fake_rect)) \
                                    and not check_for_obstacles(fake_rect, self.world.obstacles) \
                                    and not check_screen_edge(fake_rect_position):
                                # dodge 90 degree clockwise from the projectile
                                #self.velocity.x *= -1
                                #self.velocity.y = self.velocity.x
                                #self.velocity.x = y_velocity
                                self.velocity = fake_rect_position - self.position
                                self.velocity.normalize_ip()
                                self.velocity *= self.maxSpeed
                                return

                        print("undodgeable")

        # explosive projectile
            else:
                point_of_explosion: Vector2 = nearest_projectile.position + \
                    (original_velocity
                     * distance_until_despawn)
                # create a explosion object that isnt in the game so that i can see if it collides with the character
                explosion = Explosion(nearest_projectile.owner, nearest_projectile.owner.world, nearest_projectile.explosive_image,
                                      1000, point_of_explosion, nearest_projectile.owner.team_id)
                # set the x and y coordinate of the explosion (for some reason doesnt set it automatically)
                w, h = explosion.image.get_size()
                explosion.rect.x = point_of_explosion.x - w/2
                explosion.rect.y = point_of_explosion.y - h/2
                collide_list = pygame.sprite.spritecollide(
                    explosion, self.world.entities.values(), False)
                explosion_position = Vector2(
                    explosion.rect.x, explosion.rect.y)
                distance_until_explode = point_of_explosion.length() - explosion_position.length()
                if self in collide_list:
                    projectile_velocity = Vector2(
                        nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                    y_velocity = projectile_velocity.y
                    projectile_velocity.x *= -1
                    projectile_velocity.y = projectile_velocity.x
                    projectile_velocity.x = y_velocity
                    fake_velocity = Vector2(
                        projectile_velocity.x, projectile_velocity.y)
                    fake_rect = self.rect.copy()
                    character_original_velocity = fake_velocity / self.maxSpeed
                    for i in range(int(distance_until_explode)):
                        fake_rect.x = self.position.x + \
                            (character_original_velocity.x * i)
                        fake_rect.y = self.position.y + \
                            (character_original_velocity.y * i)
                        fake_rect_position = Vector2(
                            fake_rect.x, fake_rect.y)
                        # if possible to dodge
                        if not (explosion.rect.colliderect(fake_rect)) \
                                and not check_for_obstacles(fake_rect, self.world.obstacles) \
                                and not check_screen_edge(fake_rect_position):
                            # dodge 90 degree clockwise from the projectile
                            #self.velocity.x *= -1
                            #self.velocity.y = self.velocity.x
                            #self.velocity.x = y_velocity
                            self.velocity = fake_rect_position - self.position
                            self.velocity.normalize_ip()
                            self.velocity *= self.maxSpeed
                            return
                    projectile_velocity = Vector2(
                        nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                    x_velocity = projectile_velocity.x
                    projectile_velocity.y *= -1
                    projectile_velocity.x = projectile_velocity.y
                    projectile_velocity.y = x_velocity
                    fake_velocity = Vector2(
                        projectile_velocity.x, projectile_velocity.y)
                    fake_rect = self.rect.copy()
                    character_original_velocity = fake_velocity / self.maxSpeed
                    for j in range(int(distance_until_explode)):
                        fake_rect.x = self.position.x + \
                            (character_original_velocity.x * j)
                        fake_rect.y = self.position.y + \
                            (character_original_velocity.y * j)
                        fake_rect_position = Vector2(
                            fake_rect.x, fake_rect.y)
                        # if possible to dodge
                        if not (explosion.rect.colliderect(fake_rect)) \
                                and not check_for_obstacles(fake_rect, self.world.obstacles) \
                                and not check_screen_edge(fake_rect_position):
                            # dodge 90 degree clockwise from the projectile
                            #self.velocity.x *= -1
                            #self.velocity.y = self.velocity.x
                            #self.velocity.x = y_velocity
                            self.velocity = fake_rect_position - self.position
                            self.velocity.normalize_ip()
                            self.velocity *= self.maxSpeed
                            return
                    projectile_velocity = Vector2(
                        nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                    x_velocity = projectile_velocity.x
                    projectile_velocity.y *= -1
                    projectile_velocity.x *= -1
                    fake_velocity = Vector2(
                        projectile_velocity.x, projectile_velocity.y)
                    fake_rect = self.rect.copy()
                    character_original_velocity = fake_velocity / self.maxSpeed
                    for k in range(int(distance_until_explode)):
                        fake_rect.x = self.position.x + \
                            (character_original_velocity.x * k)
                        fake_rect.y = self.position.y + \
                            (character_original_velocity.y * k)
                        fake_rect_position = Vector2(
                            fake_rect.x, fake_rect.y)
                        # if possible to dodge
                        if not (explosion.rect.colliderect(fake_rect)) \
                                and not check_for_obstacles(fake_rect, self.world.obstacles) \
                                and not check_screen_edge(fake_rect_position):
                            # dodge 90 degree clockwise from the projectile
                            #self.velocity.x *= -1
                            #self.velocity.y = self.velocity.x
                            #self.velocity.x = y_velocity
                            self.velocity = fake_rect_position - self.position
                            self.velocity.normalize_ip()
                            self.velocity *= self.maxSpeed
                            return

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
        self.wizard.dodge_projectile()

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

        self.wizard.dodge_projectile()

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
