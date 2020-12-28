import pygame

from random import randint, random
from Graph import *
from Globals import *

from Character import *
from State import *
from Orc import *

class Base(Character):

    def __init__(self, world, image, orc_image, projectile_image, spawn_node_index, target_node_index):

        Character.__init__(self, world, "base", image, False)

        self.orc_image = orc_image
        self.projectile_image = projectile_image
        self.min_target_distance = 100
        self.projectile_range = 100
        self.projectile_speed = 200

        self.target = None
        self.spawn_node_index = spawn_node_index
        self.spawn_position = self.world.graph.nodes[spawn_node_index].position
        self.target_node_index = target_node_index
        
        self.spawn_cooldown = BASE_SPAWN_COOLDOWN
        self.current_spawn_cooldown = 0.

        base_state = BaseState(self)
        self.brain.add_state(base_state)


    def render(self, surface):

        Character.render(self, surface)
        

    def process(self, time_passed):
        
        Character.process(self, time_passed)
        
        if self.current_spawn_cooldown > 0:
            self.current_spawn_cooldown -= time_passed
    

class BaseState(State):

    def __init__(self, base):

        State.__init__(self, "base_state")
        self.base = base

    def do_actions(self):

        return None

    def check_conditions(self):
        
        if self.base.current_spawn_cooldown <= 0:
            self.base.current_spawn_cooldown = self.base.spawn_cooldown

            # spawn orc
            orc = Orc(self.base.world, self.base.orc_image, self.base, Vector2(self.base.spawn_position))
            orc.brain.set_state("seeking")
            orc.max_hp = ORC_MAX_HP
            orc.maxSpeed = ORC_MAX_SPEED
            orc.min_target_distance = ORC_MIN_TARGET_DISTANCE
            orc.melee_damage = ORC_MELEE_DAMAGE
            orc.melee_cooldown = ORC_MELEE_COOLDOWN
            orc.current_hp = orc.max_hp
            orc.team_id = self.base.team_id
            self.base.world.add_entity(orc)

        if self.base.current_ranged_cooldown > 0:
            return

        nearest_opponent = self.base.world.get_nearest_opponent(self.base)
        if nearest_opponent is not None:
            opponent_distance = (self.base.position - nearest_opponent.position).length()

            # opponent within range
            if opponent_distance <= self.base.min_target_distance:
                self.base.ranged_attack(nearest_opponent.position)

               
        return None

    def entry_actions(self):

        return None

