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
        self.enemy_decoy = None
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

        #picks 1/4 path at random
        self.knight.path_graph = self.knight.world.paths[randint(0, len(self.knight.world.paths)-1)]

    def do_actions(self):

        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip()
            self.knight.velocity *= self.knight.maxSpeed


    def check_conditions(self):

        # heal if knight is not full HP when seeking
        if (self.knight.current_hp < self.knight.max_hp):
            self.knight.heal()

        # check if opponent is in range
        nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
        if nearest_opponent is not None and nearest_opponent != self.knight.enemy_decoy:
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
        #node-to-node pathfinding
        self.path = pathFindAStar(self.knight.path_graph, \
                                  self.knight.path_graph.get_nearest_node(self.knight.position), \
                                  self.knight.path_graph.nodes[self.knight.base.target_node_index])

        if self.path is None:
            self.path_length = 0
        else:
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

        #if collide against its target unit, hit enemy and fall back momentarily (kiting/orb walking)
        if pygame.sprite.collide_rect(self.knight, self.knight.target):
            #self.knight.velocity = Vector2(0, 0)
            self.knight.melee_attack(self.knight.target)
            if self.knight.current_melee_cooldown == self.knight.melee_cooldown:
                self.knight.velocity = self.knight.move_target.position - self.knight.position
                if self.knight.velocity.length() > 0:
                    self.knight.velocity.normalize_ip()
                    self.knight.velocity *= self.knight.maxSpeed
        else:
            #move towards enemy and hit again if melee cooldown is about to be lifted
            if self.knight.current_melee_cooldown <= self.knight.melee_cooldown * .6:
                if self.knight.target is not None:
                    self.knight.velocity = self.knight.target.position - self.knight.position
                if self.knight.velocity.length() > 0:
                    self.knight.velocity.normalize_ip()
                    self.knight.velocity *= self.knight.maxSpeed


    def check_conditions(self):
        #if hitting base, keep hitting and dont run
        if self.knight.target.brain.active_state == "base_state":
            return None
        
        ### experimental ###
        if (self.knight.position - self.knight.move_target.position).length() < 8:
            #continue on path, and track the latest node passed
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1

        # target is gone
        if self.knight.world.get(self.knight.target.id) is None or self.knight.target.ko:
            self.knight.target = None
            self.knight.enemy_decoy = None
            if self.knight.current_hp >= self.knight.max_hp * 0.65:
                # if HP >= 65%, continue seeking
                return "seeking"
            else:
                #change to fleeing state when hp dips below 65% for testing purposes, 45% for actual game
                return "fleeing"
        # target is chasing another character (for bait/decoy situations) -> ignore the target
        elif self.knight.target.brain.active_state == "attacking" and self.knight.target.target != self.knight:
            self.knight.enemy_decoy = self.knight.target
            return "seeking"
            
        #while attacking, taking some dmg and no ally is around, flee
        if self.knight.current_hp <= self.knight.max_hp * .66:
            nearest_ally = self.knight.get_nearest_ranged_ally()
            if nearest_ally is not None:
                ally_distance = (self.knight.position - nearest_ally.position).length()
                if ally_distance >= self.knight.min_target_distance:
                    return "fleeing"
            
        return None

    def entry_actions(self):
        
        self.path = pathFindAStar(self.knight.path_graph, \
                                    self.knight.path_graph.get_nearest_node(self.knight.position), \
                                    self.knight.path_graph.nodes[self.knight.base.spawn_node_index])
        
        #self.path_to_enemy_spawn = pathFindAStar(self.knight.path_graph, \
        #                            self.knight.path_graph.get_nearest_node(self.knight.position), \
        #                            self.knight.path_graph.nodes[self.knight.base.target_node_index])

        if self.path is None:
            self.path_length = 0
        else:
            self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.knight.move_target.position = self.path[0].fromNode.position
        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position

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
        # move to targeted position
        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip()
            self.knight.velocity *= self.knight.maxSpeed

        self.knight.heal() #heal while fleeing

    def check_conditions(self):
        
        #goes back to seeking state if knight has nearby ranged ally
        nearest_ally = self.knight.get_nearest_ranged_ally()
        if nearest_ally is not None:
            ally_distance = (self.knight.position - nearest_ally.position).length()
            if (self.knight.current_hp >= self.knight.max_hp * 0.8 \
            and ally_distance <= self.knight.min_target_distance):
                return "seeking"

        #switch back to attacking state when there is a nearby enemy and HP > 90%
        nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
        if nearest_opponent is not None:
            opponent_distance = (self.knight.position - nearest_opponent.position).length()
            if opponent_distance <= self.knight.min_target_distance and self.knight.current_hp >= self.knight.max_hp * 0.9:
                    self.knight.target = nearest_opponent
                    return "attacking"
        
        if (self.knight.position - self.knight.move_target.position).length() < 8:
            #continue on path, and track the latest node passed
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None

    def entry_actions(self):
        # generate path upon fleeing
        self.path = pathFindAStar(self.knight.path_graph, \
                                self.knight.path_graph.get_nearest_node(self.knight.position), \
                                self.knight.path_graph.nodes[self.knight.base.spawn_node_index])

        if self.path is None:
            self.path_length = 0
        else:
            self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.knight.move_target.position = self.path[0].fromNode.position
        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position

        '''nearest_node = self.knight.path_graph.get_nearest_node(self.knight.position)
            further_node_index = list(self.knight.path_graph.nodes.values()).index(nearest_node)
            #take the node that's directly "behind" the further node to fall back
            nearest_node = list(self.knight.path_graph.nodes.values())[further_node_index - 1]

        self.path = pathFindAStar(self.knight.path_graph, \
                                  nearest_node, \
                                  self.knight.path_graph.nodes[self.knight.base.spawn_node_index])

        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.knight.move_target.position = self.path[0].fromNode.position

        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position'''

        return None