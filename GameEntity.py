import pygame
from pygame.locals import *

from math import *
from pygame.math import *
from Globals import *
from StateMachine import *


# ----------------------------------------------------
#   All GameEntity are Sprites
#   If show_hp is True, then a life bar will be shown
# ----------------------------------------------------
class GameEntity(pygame.sprite.Sprite):

    def __init__(self, world, name, image, show_hp = True):

        pygame.sprite.Sprite.__init__(self)

        # --- Basic attributes ---        
        self.world = world
        self.name = name
        self.image = image
        if image is not None:
            self.rect = self.image.get_rect()
            self.mask = pygame.mask.from_surface(self.image)
        self.show_hp = show_hp        

        # --- Kinematic attributes ---        
        self.position = Vector2(0, 0)
        self.orientation = 0
        self.velocity = Vector2(0, 0) 
##        self.rotation = 0.                      # rotational speed

        self.maxSpeed = 100.

        self.brain = StateMachine()

        self.id = 0
        self.team_id = 0
        self.max_hp = 100.
        self.current_hp = self.max_hp


    def render(self, surface):

        x, y = self.position
        rotated_image = pygame.transform.rotate(self.image, self.orientation)
        w, h = rotated_image.get_size()
        draw_pos = Vector2(self.position.x - w/2, self.position.y - h/2)

        surface.blit(rotated_image, draw_pos)

        # show life bar
        if self.show_hp:
            bar_x = x - w/2
            bar_y = y + h/2
            surface.fill( (255, 0, 0), (bar_x, bar_y, w, 4) )
            surface.fill( (0, 255, 0), (bar_x, bar_y, (self.current_hp / self.max_hp) * w, 4) )
        
        
    def process(self, time_passed):

        self.brain.think()

        # update position
        self.position += self.velocity * time_passed

        w, h = self.image.get_size()
        self.rect.x = self.position[0] - w/2
        self.rect.y = self.position[1] - h/2

        # detect edge of screen
        if self.position[0] < 0 or self.position[0] > SCREEN_WIDTH or \
           self.position[1] < 0 or self.position[1] > SCREEN_HEIGHT:
            if self.name == "projectile":
                self.world.remove_entity(self)
            else:
                self.position -= self.velocity * time_passed

        # --- PATCH 2021-12-14 --------------------------
        #   Made bases an obstacle
        #       to remove exploit of hiding behind a base
        # -----------------------------------------------
                
        # check if colliding with obstacle or base
        collision_list = pygame.sprite.spritecollide(self, self.world.obstacles, False, pygame.sprite.collide_mask)
        for entity in collision_list:
            if entity.team_id == self.team_id:
                continue
            elif entity.name == "obstacle" or entity.name == "base":
                self.position -= self.velocity * time_passed

        # update orientation if projectile
        if self.name == "projectile":
            self.orientation = self.getNewOrientation(self.orientation, self.velocity) % 360


    def getNewOrientation(self, currentOrientation, velocity):

        if velocity.length() > 0:
            return degrees(atan2(-velocity.y, velocity.x))
        else:
            return currentOrientation
