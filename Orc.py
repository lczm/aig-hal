import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

class Orc(Character):

    def __init__(self, world, image, base, position):

        Character.__init__(self, world, "orc", image, False)

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "orc_move_target", None)
        self.target = None

        seeking_state = OrcStateSeeking(self)
        attacking_state = OrcStateAttacking(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)
   


class OrcStateSeeking(State):

    def __init__(self, orc):

        State.__init__(self, "seeking")
        self.orc = orc

        self.path_graph = self.orc.world.paths[randint(0, len(self.orc.world.paths)-1)]

        nearest_node = self.path_graph.get_nearest_node(self.orc.position)

        self.path = pathFindAStar(self.path_graph, \
                                  nearest_node, \
                                  self.path_graph.nodes[self.orc.base.target_node_index])

        
        self.path_length = len(self.path)
        self.current_connection = 0
        self.orc.move_target.position = self.path[0].fromNode.position

    def do_actions(self):

        self.orc.velocity = self.orc.move_target.position - self.orc.position
        if self.orc.velocity.length() > 0:
            self.orc.velocity.normalize_ip();
            self.orc.velocity *= self.orc.maxSpeed

    def check_conditions(self):

        # check if opponent is in range
        nearest_opponent = self.orc.world.get_nearest_opponent(self.orc)
        if nearest_opponent is not None:
            opponent_distance = (self.orc.position - nearest_opponent.position).length()
            if opponent_distance <= self.orc.min_target_distance:
                    self.orc.target = nearest_opponent
                    return "attacking"
        
        if (self.orc.position - self.orc.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.orc.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None

    def entry_actions(self):

        nearest_node = self.path_graph.get_nearest_node(self.orc.position)

        self.path = pathFindAStar(self.path_graph, \
                                  nearest_node, \
                                  self.path_graph.nodes[self.orc.base.target_node_index])

        
        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.orc.move_target.position = self.path[0].fromNode.position

        else:
            self.orc.move_target.position = self.path_graph.nodes[self.orc.base.target_node_index].position


class OrcStateAttacking(State):

    def __init__(self, orc):

        State.__init__(self, "attacking")
        self.orc = orc

    def do_actions(self):

        # colliding with target
        if pygame.sprite.collide_rect(self.orc, self.orc.target):
            self.orc.velocity = Vector2(0, 0)
            self.orc.melee_attack(self.orc.target)

        else:
            self.orc.velocity = self.orc.target.position - self.orc.position
            if self.orc.velocity.length() > 0:
                self.orc.velocity.normalize_ip();
                self.orc.velocity *= self.orc.maxSpeed


    def check_conditions(self):

        # target is gone
        if self.orc.world.get(self.orc.target.id) is None or self.orc.target.ko:
            self.orc.target = None
            return "seeking"

        # target is too far away
        if (self.orc.target.position - self.orc.position).length() > self.orc.min_target_distance:
            return "seeking"
            
        return None

    def entry_actions(self):

        return None
