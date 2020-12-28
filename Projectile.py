import pygame

from GameEntity import *

# --- A fireball explosion that hits all opponents ---
class Explosion(GameEntity):

    def __init__(self, owner, world, image, damage, position, team_id):

        GameEntity.__init__(self, world, "explosion", image, False)

        self.owner = owner
        self.image = image
        self.damage = damage
        self.position = position
        self.team_id = team_id
        self.exploded = False
        self.exist_time = .5        # explosion stays on screen for half a second


    def render(self, surface):

        GameEntity.render(self, surface)
        

    def process(self, time_passed):

        GameEntity.process(self, time_passed)

        # --- self.exploded is set to True after the first call, so this happens only once ---
        if not self.exploded:
            collide_list = pygame.sprite.spritecollide(self, self.world.entities.values(), False, pygame.sprite.collide_mask)
            for entity in collide_list:
                if entity.team_id == self.team_id:
                    continue
                if entity.name == "projectile":
                    continue
                if entity.name == "obstacle":
                    continue
                
                entity.current_hp -= self.damage
                self.owner.xp += self.damage
                self.exploded = True

        self.exist_time -= time_passed
            
        if self.exist_time <= 0:
            self.world.remove_entity(self)


class Projectile(GameEntity):

    def __init__(self, owner, world, image, explosive_image = None):

        GameEntity.__init__(self, world, "projectile", image, False)

        self.owner = owner
        self.max_range = 100
        self.damage = 0.
        self.origin_position = Vector2(0, 0)
        self.explosive_image = explosive_image


    def render(self, surface):

        GameEntity.render(self, surface)
        

    def process(self, time_passed):

        GameEntity.process(self, time_passed)

        # normal projectiles (rocks and arrows)
        if not self.explosive_image:

            # will disappear if it reaches max_range
            if (self.position - self.origin_position).length() > self.max_range:
                self.world.remove_entity(self)
                return

            # deal damage to opponent if it collides
            else:
                collide_list = pygame.sprite.spritecollide(self, self.world.entities.values(), False, pygame.sprite.collide_mask)
                for entity in collide_list:
                    if entity.team_id == self.team_id:
                        continue
                    if entity.name == "projectile":
                        continue
                    if entity.name == "obstacle":
                        self.world.remove_entity(self)
                        return
                    
                    entity.current_hp -= self.damage
                    self.owner.xp += self.damage
                    self.world.remove_entity(self)
                    return


        # explosive projectiles - will explode when it reaches max_range
        else:
            exploded = False
            if (self.position - self.origin_position).length() >= self.max_range:
                exploded = True

            # will explode if it hits an obstacle
            if not exploded:
                collide_list = pygame.sprite.spritecollide(self, self.world.entities.values(), False, pygame.sprite.collide_mask)
                for entity in collide_list:
                    if entity.name == "obstacle":
                        exploded = True

            if exploded:
                explosion = Explosion(self.owner, self.world, self.explosive_image, self.damage, self.position, self.team_id)
                self.world.add_entity(explosion)
                self.world.remove_entity(self)
                return
