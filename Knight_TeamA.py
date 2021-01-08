import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

class Knight_TeamA(Character):

    def __init__(self, world, image, base, position):

        Character.__init__(self, world, "knight", image)

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "knight_move_target", None)
        self.target = None
        self.world = world

        self.maxSpeed = 80
        self.min_target_distance = 100
        self.melee_damage = 20
        self.melee_cooldown = 2.

        seeking_state = KnightStateSeeking_TeamA(self)
        attacking_state = KnightStateAttacking_TeamA(self)
        ko_state = KnightStateKO_TeamA(self)
        fleeing_state = KnightStateFleeing_TeamA(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(ko_state)
        self.brain.add_state(fleeing_state)

        self.brain.set_state("seeking")

    #check if knight is alone and tanking for nothing lol
    def get_nearest_ranged_ally(self):

        nearest_ranged_ally = None
        ranged_units = ["wizard", "archer"]
        distance = 0.

        for entity in self.world.entities.values():
            if entity.team_id != self.team_id:
                continue
            if entity.name not in ranged_units:
                continue
            if entity.ko:
                continue

            if nearest_ranged_ally is None:
                nearest_ranged_ally = entity
                distance = (self.position - entity.position).length()
            else:
                if distance > (self.position - entity.position).length():
                    distance = (self.position - entity.position).length()
                    nearest_ranged_ally = entity
        
        return nearest_ranged_ally

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)

        level_up_stats = ["hp", "speed", "melee damage", "melee cooldown"]
        if self.can_level_up():
            choice = 0 #always hp
            self.level_up(level_up_stats[choice])

   


class KnightStateSeeking_TeamA(State):

    def __init__(self, knight):

        State.__init__(self, "seeking")
        self.knight = knight

        self.knight.path_graph = self.knight.world.paths[randint(0, len(self.knight.world.paths)-1)] #picks 1/4 path at random


    def do_actions(self):

        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip();
            self.knight.velocity *= self.knight.maxSpeed


    def check_conditions(self):

        # check if opponent is in range
        nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
        if nearest_opponent is not None:
            opponent_distance = (self.knight.position - nearest_opponent.position).length()
            if opponent_distance <= self.knight.min_target_distance:
                    self.knight.target = nearest_opponent
                    return "attacking"
        
        if (self.knight.position - self.knight.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None


    def entry_actions(self):
        #plans to include further nodes but within the same path function
        nearest_node = self.knight.path_graph.get_nearest_node(self.knight.position)

        self.path = pathFindAStar(self.knight.path_graph, \
                                  nearest_node, \
                                  self.knight.path_graph.nodes[self.knight.base.target_node_index])

        
        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.knight.move_target.position = self.path[0].fromNode.position

        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.target_node_index].position


class KnightStateAttacking_TeamA(State):

    def __init__(self, knight):

        State.__init__(self, "attacking")
        self.knight = knight

    def do_actions(self):
        # colliding with target
        if pygame.sprite.collide_rect(self.knight, self.knight.target):
            self.knight.velocity = Vector2(0, 0)
            self.knight.melee_attack(self.knight.target)
            if self.knight.current_melee_cooldown == self.knight.melee_cooldown:
                self.knight.velocity = self.knight.target.position - self.knight.position
                self.knight.velocity.normalize_ip()
                self.knight.velocity *= -self.knight.maxSpeed
        else:
            if self.knight.current_melee_cooldown <= self.knight.melee_cooldown * .6:
                self.knight.velocity = self.knight.target.position - self.knight.position
                if self.knight.velocity.length() > 0:
                    self.knight.velocity.normalize_ip()
                    self.knight.velocity *= self.knight.maxSpeed


    def check_conditions(self):

        # target is gone
        if self.knight.world.get(self.knight.target.id) is None or self.knight.target.ko:
            self.knight.target = None
            if self.knight.current_hp >= self.knight.max_hp * 0.8:
                # if HP >= 80%, continue seeking
                return "seeking"
            else:
                #change to fleeing state when hp dips below 80%, and use heal
                return "fleeing"
        
        #while attacking, taking some dmg and no ally is around, flee
        if self.knight.current_hp <= self.knight.max_hp * .66:
            nearest_ally = self.knight.get_nearest_ranged_ally()
            if nearest_ally is not None:
                ally_distance = (self.knight.position - nearest_ally.position).length()
                if ally_distance >= self.knight.min_target_distance:
                    return "fleeing"
            
        return None

    def entry_actions(self):

        return None


class KnightStateKO_TeamA(State):

    def __init__(self, knight):

        State.__init__(self, "ko")
        self.knight = knight

    def do_actions(self):

        return None


    def check_conditions(self):

        # respawned
        if self.knight.current_respawn_time <= 0:
            self.knight.current_respawn_time = self.knight.respawn_time
            self.knight.ko = False
            self.knight.path_graph = self.knight.world.paths[randint(0, len(self.knight.world.paths)-1)]
            return "seeking"
            
        return None

    def entry_actions(self):

        self.knight.current_hp = self.knight.max_hp
        self.knight.position = Vector2(self.knight.base.spawn_position)
        self.knight.velocity = Vector2(0, 0)
        self.knight.target = None

        return None

class KnightStateFleeing_TeamA(State):

    def __init__(self, knight):

        State.__init__(self, "fleeing")
        self.knight = knight

    def do_actions(self):

        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip()
            self.knight.velocity *= self.knight.maxSpeed

        self.knight.heal() #heal while fleeing

    def check_conditions(self):
        
        nearest_ally = self.knight.get_nearest_ranged_ally()
        if nearest_ally is not None:
            ally_distance = (self.knight.position - nearest_ally.position).length()
            if (self.knight.current_hp >= self.knight.max_hp) \
            or (self.knight.current_hp >= self.knight.max_hp * 0.8 \
            and ally_distance <= self.knight.min_target_distance):
                return "seeking"

        nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
        if nearest_opponent is not None:
            opponent_distance = (self.knight.position - nearest_opponent.position).length()
            if opponent_distance <= self.knight.min_target_distance and self.knight.current_hp >= self.knight.max_hp * 0.9:
                    self.knight.target = nearest_opponent
                    return "attacking"
        
        if (self.knight.position - self.knight.move_target.position).length() < 8:
            # continue on path
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None

    def entry_actions(self):
        nearest_node = self.knight.path_graph.get_nearest_node(self.knight.position)

        self.path = pathFindAStar(self.knight.path_graph, \
                                  nearest_node, \
                                  self.knight.path_graph.nodes[self.knight.base.spawn_node_index])

        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.knight.move_target.position = self.path[0].fromNode.position

        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position