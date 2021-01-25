import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *
from Utils_Mayasol import *

class Knight_TeamMayasol(Character):

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
        self.min_defence_distance = 175
        self.melee_damage = 20
        self.melee_cooldown = 2.
        self.enemy_locations = get_enemies_positions_in_lanes(self.world.paths, self)

        seeking_state = KnightStateSeeking_TeamMayasol(self)
        attacking_state = KnightStateAttacking_TeamMayasol(self)
        ko_state = KnightStateKO_TeamMayasol(self)
        fleeing_state = KnightStateFleeing_TeamMayasol(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(ko_state)
        self.brain.add_state(fleeing_state)

        self.brain.set_state("seeking")

    #check if knight is alone and tanking for nothing
    def get_nearest_ranged_ally(self, character):

        nearest_ranged_ally = None
        distance = 0.

        for entity in self.world.entities.values():
            if entity.team_id != self.team_id:
                continue
            if entity.name != character:
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

    def defend(self):
        for lane in self.enemy_locations:
            # knight(4) + archer(4) + wizard(6)
            if self.enemy_locations[lane] >= 14:
                return True

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)

        level_up_stats = ["hp", "speed", "melee damage", "melee cooldown"]
        if self.can_level_up():
            choice = 0 #always hp
            self.level_up(level_up_stats[choice])


class KnightStateSeeking_TeamMayasol(State):

    def __init__(self, knight):

        State.__init__(self, "seeking")
        self.knight = knight

        #picks 1/4 path at random
        self.knight.path_graph = self.knight.world.paths[1]

    def do_actions(self):

        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip()
            self.knight.velocity *= self.knight.maxSpeed

        self.knight.enemy_locations = lane_threat(self.knight.world.paths, self.knight)

        # heal if knight HP is below 90% when seeking
        if (self.knight.current_hp <= self.knight.max_hp * 0.9):
            self.knight.heal()

    def check_conditions(self):

        if self.knight.defend():
            return "fleeing"

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
        self.knight.target = None

        #node-to-node pathfinding
        self.path = get_path_to_enemy_base(self.knight, self.knight.path_graph, self.knight.position)

        if self.path is None:
            self.path_length = 0
        else:
            self.path_length = len(self.path)

        self.current_connection = 0

        if (self.path_length > 0):
            self.knight.move_target.position = self.path[0].fromNode.position
        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.target_node_index].position


class KnightStateAttacking_TeamMayasol(State):

    def __init__(self, knight):

        State.__init__(self, "attacking")
        self.knight = knight

    def do_actions(self):

        self.knight.enemy_locations = lane_threat(self.knight.world.paths, self.knight)

        #if collide against its target unit, hit enemy and fall back momentarily (kiting/orb walking)
        if pygame.sprite.collide_rect(self.knight, self.knight.target):
            #if wizard around me and hp < 60%:
            #    heal instead of attack
            if self.knight.current_hp <= self.knight.max_hp * 0.6:
                nearest_ally = self.knight.get_nearest_ranged_ally("wizard")
                if nearest_ally is not None:
                    ally_distance = (self.knight.position - nearest_ally.position).length()
                    if ally_distance <= self.knight.min_defence_distance:
                        self.knight.heal()

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
        if (self.knight.position - self.knight.move_target.position).length() < 8:
            #continue on path, and track the latest node passed
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1

        #if hitting base, keep hitting and dont run
        if self.knight.target.brain.active_state == "base_state":
            return None


        # target is gone
        if self.knight.world.get(self.knight.target.id) is None or self.knight.target.ko:
            if self.knight.defend() == True:
                return "fleeing"
            else:
                return "seeking"

        # target is chasing another character (for bait/decoy situations) -> ignore the target
        elif self.knight.target.brain.active_state == "attacking" and self.knight.target.target != self.knight:
            self.knight.enemy_decoy = self.knight.target
            return "seeking"
            
        #while attacking, taking some dmg and no ally is around, flee
        if self.knight.current_hp <= self.knight.max_hp * .6:
            nearest_ally = self.knight.get_nearest_ranged_ally("wizard")
            if nearest_ally is not None:
                ally_distance = (self.knight.position - nearest_ally.position).length()
                if ally_distance >= self.knight.min_defence_distance:
                    return "fleeing"
            
        return None

    def entry_actions(self):
        
        self.path = get_path_to_my_base(self.knight, self.knight.path_graph, self.knight.position)

        if self.path is None:
            self.path_length = 0
        else:
            self.path_length = len(self.path)

        self.current_connection = 0

        if (self.path_length > 0):
            self.knight.move_target.position = self.path[0].fromNode.position
        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position

        return None


class KnightStateKO_TeamMayasol(State):

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
            self.knight.path_graph = self.knight.world.paths[1]
            return "seeking"
            
        return None

    def entry_actions(self):

        self.knight.current_hp = self.knight.max_hp
        self.knight.position = Vector2(self.knight.base.spawn_position)
        self.knight.velocity = Vector2(0, 0)
        self.knight.target = None

        return None

class KnightStateFleeing_TeamMayasol(State):

    def __init__(self, knight):

        State.__init__(self, "fleeing")
        self.knight = knight

    def do_actions(self):
        
        self.knight.enemy_locations = lane_threat(self.knight.world.paths, self.knight)

        # move to targeted position
        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip()
            self.knight.velocity *= self.knight.maxSpeed

        self.knight.heal() #heal while fleeing

    def check_conditions(self):
        
        #goes back to seeking state if knight has nearby ranged ally
        nearest_ally = self.knight.get_nearest_ranged_ally("wizard")
        if nearest_ally is not None:
            ally_distance = (self.knight.position - nearest_ally.position).length()
            if (self.knight.current_hp >= self.knight.max_hp * 0.8 \
            and ally_distance <= self.knight.min_target_distance):
                return "seeking"

        if (self.knight.position - self.knight.move_target.position).length() < 8:
            #continue on path
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1

        #in defense mode
        if self.knight.defend():
            if (self.knight.position - self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position).length() < 8:
                nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
                if nearest_opponent is not None:
                    opponent_distance = (self.knight.position - nearest_opponent.position).length()
                    if opponent_distance <= self.knight.min_defence_distance:
                            self.knight.target = nearest_opponent
                            return "attacking"
        else:
            # outside of defense mode
            # switch back to attacking state when there is a nearby enemy and HP > 85%
            nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
            if nearest_opponent is not None:
                opponent_distance = (self.knight.position - nearest_opponent.position).length()
                if opponent_distance <= self.knight.min_target_distance and self.knight.current_hp >= self.knight.max_hp * 0.85:
                        self.knight.target = nearest_opponent
                        return "attacking"
            
        return None

    def entry_actions(self):

        self.knight.target = None
        self.knight.enemy_decoy = None

        # generate path upon fleeing
        self.path = get_path_to_my_base(self.knight, self.knight.path_graph, self.knight.position)

        if self.path is None:
            self.path_length = 0
        else:
            self.path_length = len(self.path)

        self.current_connection = 0

        if (self.path_length > 0):
            self.knight.move_target.position = self.path[0].fromNode.position
        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.spawn_node_index].position

        return None