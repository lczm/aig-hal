from Globals import *

from GameEntity import *
from Projectile import *



class Character(GameEntity):

    def __init__(self, world, name, image, respawnable = True):
        
        GameEntity.__init__(self, world, name, image)

        # --- Combat attributes ---
        self.melee_damage = 0
        self.melee_cooldown = 1.5
        self.current_melee_cooldown = 0

        self.ranged_damage = 0
        self.ranged_cooldown = 3.
        self.current_ranged_cooldown = 0

        self.min_target_distance = 100          # distance within which character will switch to attack mode
        
        # -- Respawn attributes ---
        self.ko = False
        self.respawnable = respawnable
        self.respawn_time = RESPAWN_TIME
        self.current_respawn_time = self.respawn_time

        # -- Healing attributes --
        self.healing_cooldown = HEALING_COOLDOWN
        self.current_healing_cooldown = 0
        self.healing_percentage = HEALING_PERCENTAGE

        # -- Level up attributes --
        self.xp = 0
        self.xp_to_next_level = XP_TO_LEVEL
        self.level_up_message = None
        self.level_up_y = 0


    def process(self, time_passed):

        GameEntity.process(self, time_passed)

        # check for death
        if self.current_hp <= 0:

            # add scores for opposing team
            if self.name == "orc":
                print(TEAM_NAME[self.team_id] + " Orc killed")
                self.world.scores[1 - self.team_id] += 10
            elif self.name == "knight":
                print(TEAM_NAME[self.team_id] + " Knight killed")
                self.world.scores[1 - self.team_id] += 40
            elif self.name == "archer":
                print(TEAM_NAME[self.team_id] + " Archer killed")
                self.world.scores[1 - self.team_id] += 40
            elif self.name == "wizard":
                print(TEAM_NAME[self.team_id] + " Wizard killed")
                self.world.scores[1 - self.team_id] += 40
            elif self.name == "tower":
                print(TEAM_NAME[self.team_id] + " Tower killed")
                self.world.scores[1 - self.team_id] += 200
            elif self.name == "base":
                print(TEAM_NAME[self.team_id] + " Base killed")
                self.world.scores[1 - self.team_id] += 500

            # set heroes to ko
            if self.respawnable:
                self.ko = True
                self.brain.set_state("ko")

            # if not a hero, just remove it
            else:
                self.world.remove_entity(self)
                return

        # update cooldown timers

        # --- PATCH 2021-12-14 ---------------------------------
        #   Healing cooldown now on top of melee/ranged cooldown
        #       to remove the "heal for free" exploit
        # ------------------------------------------------------
        if self.current_healing_cooldown > 0:
            self.current_healing_cooldown -= time_passed

        else:       
            if self.current_melee_cooldown > 0:
                self.current_melee_cooldown -= time_passed

            if self.current_ranged_cooldown > 0:
                self.current_ranged_cooldown -= time_passed

        if self.ko:
            self.current_respawn_time -= time_passed
            
    # --- Deals melee damage to target if you are colliding with it ---
    def melee_attack(self, target):

        # --- PATCH 2020-01-13 --------------------
        #   Removed friendly fire for melee attacks
        # -----------------------------------------
        if self.team_id == target.team_id:
            return
        
        if self.current_healing_cooldown <= 0:
            
            # colliding with target
            if pygame.sprite.collide_rect(self, self.target):
                if self.current_melee_cooldown <= 0:
                    self.target.current_hp -= self.melee_damage
                    self.current_melee_cooldown = self.melee_cooldown
                    self.xp += self.melee_damage


    # -----------------------------------------------------------------
    #   Creates a projectile that deals ranged damage
    #   If explosive_image is None, the projectile is an arrow
    #       - Travels until it hits an opponent
    #
    #   If explosive_image is not None, the projectile is a fireball
    #       - Travels until it reaches target_position, then explodes
    #       - Damages all opponents colliding with explosive_image
    # -----------------------------------------------------------------
    def ranged_attack(self, target_position, explosive_image = None):

        if self.current_healing_cooldown <= 0 and self.current_ranged_cooldown <= 0:
            
            projectile = Projectile(self, self.world, self.projectile_image, explosive_image)

            if explosive_image:
                distance = (self.position - target_position).length()
                projectile.max_range = min(distance, self.projectile_range)
            else:
                projectile.max_range = self.projectile_range
            
            projectile.maxSpeed = self.projectile_speed
            projectile.damage = self.ranged_damage
            projectile.team_id = self.team_id
            projectile.position = Vector2(self.position)
            projectile.origin_position = Vector2(self.position)
            projectile.velocity = target_position - projectile.position
            projectile.velocity.normalize_ip()
            projectile.velocity *= projectile.maxSpeed
            
            self.world.add_entity(projectile)
            self.current_ranged_cooldown = self.ranged_cooldown


    # --- Heals self. Units who have healed cannot attack for self.healing_cooldown seconds ---
    def heal(self):

        if self.current_healing_cooldown <= 0:
            self.current_hp = min(self.current_hp + self.max_hp * self.healing_percentage / 100, self.max_hp)
            self.current_healing_cooldown = self.healing_cooldown
            print(TEAM_NAME[self.team_id] + " " + self.name + " healed up to " + str(self.current_hp))


    def render(self, surface):
        if not self.ko:
            GameEntity.render(self, surface)

        # --- Visual feedback on level up ---
        if self.level_up_message:
            font = pygame.font.SysFont("comicsansms", 18, True)
            msg = font.render("+" + self.level_up_message, True, (255, 255, 255))
            w, h = font.size("+" + self.level_up_message)
            surface.blit(msg, (self.position[0] - w/2, self.position[1] - h/2 - self.level_up_y))
            self.level_up_y += 1
            if self.level_up_y == 40:
                self.level_up_y = 0
                self.level_up_message = None

        # --- If DEBUG is on, shows min_target_distance and target ---
        if DEBUG:
            pygame.draw.circle(surface, (0, 0, 0), (int(self.position[0]), int(self.position[1])), int(self.min_target_distance), int(2))

            font = pygame.font.SysFont("arial", 12, True)
            state_name = font.render(self.brain.active_state.name, True, (255, 255, 255))
            surface.blit(state_name, self.position)

            if self.target:
                pygame.draw.line(surface, (0, 255, 0), self.position, self.target.position)


    def can_level_up(self):
        return self.xp >= self.xp_to_next_level
                

    # --- Levels up the given stat. Does nothing if there is not enough XP to level ---
    def level_up(self, stat):

        if self.xp < self.xp_to_next_level:
            return

        if stat == "hp":
            amount = self.max_hp * UP_PERCENTAGE_HP / 100
            self.max_hp += amount
            self.current_hp += amount
        elif stat == "speed":
            amount = self.maxSpeed * UP_PERCENTAGE_SPEED / 100
            self.maxSpeed += amount
        elif stat == "melee damage":
            amount = self.melee_damage * UP_PERCENTAGE_MELEE_DAMAGE / 100
            self.melee_damage += amount
        elif stat == "melee cooldown":
            amount = self.melee_cooldown * UP_PERCENTAGE_MELEE_COOLDOWN / 100
            self.melee_cooldown -= amount
            self.current_melee_cooldown -= amount
        elif stat == "ranged damage":
            amount = self.ranged_damage * UP_PERCENTAGE_RANGED_DAMAGE / 100
            self.ranged_damage += amount
        elif stat == "ranged cooldown":
            amount = self.ranged_cooldown * UP_PERCENTAGE_RANGED_COOLDOWN / 100
            self.ranged_cooldown -= amount
            self.current_ranged_cooldown -= amount
        elif stat == "projectile range":
            amount = self.projectile_range * UP_PERCENTAGE_PROJECTILE_RANGE / 100
            self.projectile_range += amount
        elif stat == "healing":
            amount = self.healing_percentage * UP_PERCENTAGE_HEALING / 100
            self.healing_percentage += amount
        elif stat == "healing cooldown":
            amount = self.healing_cooldown * UP_PERCENTAGE_HEALING_COOLDOWN / 100
            self.healing_cooldown -= amount
            self.current_healing_cooldown -= amount
        else:
            return

        self.xp -= self.xp_to_next_level
        self.xp_to_next_level += XP_TO_LEVEL
        print(TEAM_NAME[self.team_id] + " " + self.name + " leveled up " + stat + " by " + str(amount))
        self.level_up_message = stat

