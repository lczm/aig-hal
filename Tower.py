import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

class Tower(Character):

    def __init__(self, world, image, projectile_image):

        Character.__init__(self, world, "tower", image, False)

        self.target = None
        self.projectile_image = projectile_image

        self.min_target_distance = 100
        self.projectile_range = 100
        self.projectile_speed = 200

        tower_state = TowerState(self)
        self.brain.add_state(tower_state)


    def render(self, surface):

        Character.render(self, surface)
    

class TowerState(State):

    def __init__(self, tower):

        State.__init__(self, "tower_state")
        self.tower = tower

    def do_actions(self):

        return None

    def check_conditions(self):

        if self.tower.current_ranged_cooldown > 0:
            return

        nearest_opponent = self.tower.world.get_nearest_opponent(self.tower)
        if nearest_opponent is not None:
            opponent_distance = (self.tower.position - nearest_opponent.position).length()

            # opponent within range
            if opponent_distance <= self.tower.min_target_distance:
                self.tower.ranged_attack(nearest_opponent.position)
                
               
        return None

    def entry_actions(self):

        return None

