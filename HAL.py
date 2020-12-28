import pygame
from pygame.locals import *

from random import randint, random
from math import *
from pygame.math import *

from Globals import *
from State import *
from StateMachine import *
from Graph import *

from GameEntity import *
from Character import *
from Orc import *
from Tower import *
from Base import *

from Knight_TeamA import *
from Archer_TeamA import *
from Wizard_TeamA import *

from Knight_TeamB import *
from Archer_TeamB import *
from Wizard_TeamB import *


class World(object):

    def __init__(self):

        self.entities = {}
        self.entity_id = 0
        self.obstacles = []
        self.background = pygame.image.load("assets\grass_bkgrd_1024_768.png").convert_alpha()

        self.graph = Graph(self)
        self.generate_pathfinding_graphs("pathfinding_graph.txt")
        self.scores = [0, 0]

        self.countdown_timer = TIME_LIMIT
        self.game_end = False
        

    # --- Reads a set of pathfinding graphs from a file ---
    def generate_pathfinding_graphs(self, filename):

        f = open(filename, "r")

        # Create the nodes
        line = f.readline()
        while line != "connections\n":
            data = line.split()
            self.graph.nodes[int(data[0])] = Node(self.graph, int(data[0]), int(data[1]), int(data[2]))
            line = f.readline()

        # Create the connections
        line = f.readline()
        while line != "paths\n":
            data = line.split()
            node0 = int(data[0])
            node1 = int(data[1])
            distance = (Vector2(self.graph.nodes[node0].position) - Vector2(self.graph.nodes[node1].position)).length()
            self.graph.nodes[node0].addConnection(self.graph.nodes[node1], distance)
            self.graph.nodes[node1].addConnection(self.graph.nodes[node0], distance)
            line = f.readline()

        # Create the orc paths, which are also Graphs
        self.paths = []
        line = f.readline()
        while line != "":
            path = Graph(self)
            data = line.split()
            
            # Create the nodes
            for i in range(0, len(data)):
                node = self.graph.nodes[int(data[i])]
                path.nodes[int(data[i])] = Node(path, int(data[i]), node.position[0], node.position[1])

            # Create the connections
            for i in range(0, len(data)-1):
                node0 = int(data[i])
                node1 = int(data[i + 1])
                distance = (Vector2(self.graph.nodes[node0].position) - Vector2(self.graph.nodes[node1].position)).length()
                path.nodes[node0].addConnection(path.nodes[node1], distance)
                path.nodes[node1].addConnection(path.nodes[node0], distance)
                
            self.paths.append(path)

            line = f.readline()

        f.close()


    def add_entity(self, entity):

        self.entities[self.entity_id] = entity
        entity.id = self.entity_id
        self.entity_id += 1


    def remove_entity(self, entity):

        if entity.name == "base":
            self.game_end = True
            self.game_result = TEAM_NAME[1 - entity.team_id] + " wins!"
            self.final_scores = "Time left - " + str(int(self.countdown_timer)) + " (base destroyed)"

        if entity.id in self.entities.keys():
            del self.entities[entity.id]


    def get(self, entity_id):

        if entity_id in self.entities:
            return self.entities[entity_id]

        else:
            return None


    def process(self, time_passed):

        time_passed_seconds = time_passed / 1000.0
        for entity in list(self.entities.values()):
            entity.process(time_passed_seconds)

        # --- Reduces the overall countdown timer
        self.countdown_timer -= time_passed_seconds

        # --- Checks if game has ended due to running out of time ---
        if self.countdown_timer <= 0:
            self.game_end = True

            if self.scores[0] > self.scores[1]:
                self.game_result = TEAM_NAME[0] + " wins!"
                self.final_scores = str(self.scores[0]) + " - " + str(self.scores[1])
            elif self.scores[1] > self.scores[0]:
                self.game_result = TEAM_NAME[1] + " wins!"
                self.final_scores = str(self.scores[1]) + " - " + str(self.scores[0])
            else:
                self.game_result = "DRAW"
                self.final_scores = str(self.scores[0]) + " - " + str(self.scores[1])
            

    def render(self, surface):

        # draw background and text
        surface.blit(self.background, (0, 0))

        # draw graph if SHOW_PATHS is true
        if SHOW_PATHS:
            self.graph.render(surface)

        # draw all entities
        for entity in self.entities.values():
            entity.render(surface)

        # draw the scores
        font = pygame.font.SysFont("arial", 24, True)
        
        blue_score = font.render(TEAM_NAME[0] + " score = " + str(self.scores[0]), True, (0, 0, 255))
        surface.blit(blue_score, (150, 10))

        red_score = font.render(TEAM_NAME[1] + " score = " + str(self.scores[1]), True, (255, 0, 0))
        surface.blit(red_score, (870 - red_score.get_size()[0], 730))

        # draw the countdown timer
        timer = font.render(str("Time left = " + str(int(self.countdown_timer))), True, (255, 255, 255))
        w, h = timer.get_size()
        surface.blit(timer, (SCREEN_WIDTH // 2 - w//2 , SCREEN_HEIGHT // 2 - h//2))

        # game end
        if self.game_end:
            end_font = pygame.font.SysFont("arial", 60, True)
            
            msg = end_font.render(self.game_result, True, (255, 255, 255))
            w, h = msg.get_size()
            surface.blit(msg, (SCREEN_WIDTH // 2 - w//2 , SCREEN_HEIGHT // 2 - h//2 - 200))

            msg = end_font.render(self.final_scores, True, (255, 255, 255))
            w, h = msg.get_size()
            surface.blit(msg, (SCREEN_WIDTH // 2 - w//2 , SCREEN_HEIGHT // 2 - h//2 - 100))


    def get_entity(self, name):

        for entity in self.entities.values():
            if entity.name == name:
                return entity
        
        return None

    # --- returns the nearest opponent, which is a non-projectile, character from the opposing team that is not ko'd ---    
    def get_nearest_opponent(self, char):

        nearest_opponent = None
        distance = 0.

        for entity in self.entities.values():

            # neutral entity
            if entity.team_id == 2:
                continue

            # same team
            if entity.team_id == char.team_id:
                continue

            if entity.name == "projectile" or entity.name == "explosion":
                continue

            if entity.ko:
                continue

            if nearest_opponent is None:
                nearest_opponent = entity
                distance = (char.position - entity.position).length()
            else:
                if distance > (char.position - entity.position).length():
                    distance = (char.position - entity.position).length()
                    nearest_opponent = entity
        
        return nearest_opponent



class Obstacle(GameEntity):

    def __init__(self, world, image):

        GameEntity.__init__(self, world, "obstacle", image, False)

    def render(self, surface):

        GameEntity.render(self, surface)

    def process(self, time_passed):

        GameEntity.process(self, time_passed)
        


def run():

    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE, 0, 32)

    world = World()

    w, h = SCREEN_SIZE

    # --- Load images ---
    blue_base_image = pygame.image.load("assets/blue_base.png").convert_alpha()
    blue_orc_image = pygame.image.load("assets/blue_orc_32_32.png").convert_alpha()
    blue_tower_image = pygame.image.load("assets/blue_tower.png").convert_alpha()
    blue_rock_image = pygame.image.load("assets/blue_rock.png").convert_alpha()
    blue_knight_image = pygame.image.load("assets/blue_knight_32_32.png").convert_alpha()
    blue_archer_image = pygame.image.load("assets/blue_archer_32_32.png").convert_alpha()
    blue_arrow_image = pygame.image.load("assets/blue_arrow.png").convert_alpha()
    blue_wizard_image = pygame.image.load("assets/blue_wizard_32_32.png").convert_alpha()
    blue_explosion_image = pygame.image.load("assets/blue_explosion.png").convert_alpha()

    red_base_image = pygame.image.load("assets/red_base.png").convert_alpha()
    red_orc_image = pygame.image.load("assets/red_orc_32_32.png").convert_alpha()
    red_tower_image = pygame.image.load("assets/red_tower.png").convert_alpha()
    red_rock_image = pygame.image.load("assets/red_rock.png").convert_alpha()
    red_knight_image = pygame.image.load("assets/red_knight_32_32.png").convert_alpha()
    red_archer_image = pygame.image.load("assets/red_archer_32_32.png").convert_alpha()
    red_arrow_image = pygame.image.load("assets/red_arrow.png").convert_alpha()
    red_wizard_image = pygame.image.load("assets/red_wizard_32_32.png").convert_alpha()
    red_explosion_image = pygame.image.load("assets/red_explosion.png").convert_alpha()

    grey_tower_image = pygame.image.load("assets/grey_tower.png").convert_alpha()
    grey_projectile_image = pygame.image.load("assets/grey_rock.png").convert_alpha()
    mountain_image_1 = pygame.image.load("assets/mountain_1.png").convert_alpha()
    mountain_image_2 = pygame.image.load("assets/mountain_2.png").convert_alpha()
    plateau_image = pygame.image.load("assets/plateau.png").convert_alpha()


    # --- Initialize Blue buildings and units ---
    blue_base = Base(world, blue_base_image, blue_orc_image, blue_rock_image, 0, 4)
    blue_base.position = Vector2(68, 68)
    blue_base.team_id = 0
    blue_base.max_hp = BASE_MAX_HP
    blue_base.min_target_distance = BASE_MIN_TARGET_DISTANCE
    blue_base.projectile_range = BASE_PROJECTILE_RANGE
    blue_base.projectile_speed = BASE_PROJECTILE_SPEED
    blue_base.ranged_damage = BASE_RANGED_DAMAGE
    blue_base.ranged_cooldown = BASE_RANGED_COOLDOWN
    blue_base.current_hp = blue_base.max_hp
    blue_base.brain.set_state("base_state")
    world.add_entity(blue_base)

    blue_tower_1 = Tower(world, blue_tower_image, blue_rock_image)
    blue_tower_1.position = Vector2(200, 100)
    blue_tower_1.team_id = 0
    blue_tower_1.max_hp = TOWER_MAX_HP
    blue_tower_1.min_target_distance = TOWER_MIN_TARGET_DISTANCE
    blue_tower_1.projectile_range = TOWER_PROJECTILE_RANGE
    blue_tower_1.projectile_speed = TOWER_PROJECTILE_SPEED
    blue_tower_1.ranged_damage = TOWER_RANGED_DAMAGE
    blue_tower_1.ranged_cooldown = TOWER_RANGED_COOLDOWN
    blue_tower_1.current_hp = blue_tower_1.max_hp
    blue_tower_1.brain.set_state("tower_state")
    world.add_entity(blue_tower_1)

    blue_tower_2 = Tower(world, blue_tower_image, blue_rock_image)
    blue_tower_2.position = Vector2(105, 190)
    blue_tower_2.team_id = 0
    blue_tower_2.max_hp = TOWER_MAX_HP
    blue_tower_2.min_target_distance = TOWER_MIN_TARGET_DISTANCE
    blue_tower_2.projectile_range = TOWER_PROJECTILE_RANGE
    blue_tower_2.projectile_speed = TOWER_PROJECTILE_SPEED
    blue_tower_2.ranged_damage = TOWER_RANGED_DAMAGE
    blue_tower_2.ranged_cooldown = TOWER_RANGED_COOLDOWN
    blue_tower_2.current_hp = blue_tower_2.max_hp
    blue_tower_2.brain.set_state("tower_state")
    world.add_entity(blue_tower_2)

    blue_knight = Knight_TeamA(world, blue_knight_image, blue_base, Vector2(blue_base.spawn_position))
    blue_knight.team_id = 0
    blue_knight.max_hp = KNIGHT_MAX_HP
    blue_knight.maxSpeed = KNIGHT_MAX_SPEED
    blue_knight.min_target_distance = KNIGHT_MIN_TARGET_DISTANCE
    blue_knight.melee_damage = KNIGHT_MELEE_DAMAGE
    blue_knight.melee_cooldown = KNIGHT_MELEE_COOLDOWN
    blue_knight.current_hp = blue_knight.max_hp
    world.add_entity(blue_knight)

    blue_archer = Archer_TeamA(world, blue_archer_image, blue_arrow_image, blue_base, Vector2(blue_base.spawn_position))
    blue_archer.team_id = 0
    blue_archer.max_hp = ARCHER_MAX_HP
    blue_archer.maxSpeed = ARCHER_MAX_SPEED
    blue_archer.min_target_distance = ARCHER_MIN_TARGET_DISTANCE
    blue_archer.projectile_range = ARCHER_PROJECTILE_RANGE
    blue_archer.projectile_speed = ARCHER_PROJECTILE_SPEED
    blue_archer.ranged_damage = ARCHER_RANGED_DAMAGE
    blue_archer.ranged_cooldown = ARCHER_RANGED_COOLDOWN
    blue_archer.current_hp = blue_archer.max_hp
    world.add_entity(blue_archer)

    blue_wizard = Wizard_TeamA(world, blue_wizard_image, blue_rock_image, blue_base, Vector2(blue_base.spawn_position), blue_explosion_image)
    blue_wizard.team_id = 0
    blue_wizard.max_hp = WIZARD_MAX_HP
    blue_wizard.maxSpeed = WIZARD_MAX_SPEED
    blue_wizard.min_target_distance = WIZARD_MIN_TARGET_DISTANCE
    blue_wizard.projectile_range = WIZARD_PROJECTILE_RANGE
    blue_wizard.projectile_speed = WIZARD_PROJECTILE_SPEED
    blue_wizard.ranged_damage = WIZARD_RANGED_DAMAGE
    blue_wizard.ranged_cooldown = WIZARD_RANGED_COOLDOWN
    blue_wizard.current_hp = blue_wizard.max_hp
    world.add_entity(blue_wizard)


    # --- Initialize Red buildings and units ---
    red_base = Base(world, red_base_image, red_orc_image, red_rock_image, 4, 0)
    red_base.position = Vector2(SCREEN_WIDTH - 68, SCREEN_HEIGHT - 68)
    red_base.team_id = 1
    red_base.max_hp = BASE_MAX_HP * RED_MULTIPLIER
    red_base.min_target_distance = BASE_MIN_TARGET_DISTANCE
    red_base.projectile_range = BASE_PROJECTILE_RANGE
    red_base.projectile_speed = BASE_PROJECTILE_SPEED
    red_base.ranged_damage = BASE_RANGED_DAMAGE * RED_MULTIPLIER
    red_base.ranged_cooldown = BASE_RANGED_COOLDOWN
    red_base.current_hp = red_base.max_hp
    red_base.brain.set_state("base_state")
    world.add_entity(red_base)

    red_tower_1 = Tower(world, red_tower_image, red_rock_image)
    red_tower_1.position = Vector2(820, 660)
    red_tower_1.team_id = 1
    red_tower_1.max_hp = TOWER_MAX_HP * RED_MULTIPLIER
    red_tower_1.min_target_distance = TOWER_MIN_TARGET_DISTANCE
    red_tower_1.projectile_range = TOWER_PROJECTILE_RANGE
    red_tower_1.projectile_speed = TOWER_PROJECTILE_SPEED
    red_tower_1.ranged_damage = TOWER_RANGED_DAMAGE * RED_MULTIPLIER
    red_tower_1.ranged_cooldown = TOWER_RANGED_COOLDOWN
    red_tower_1.current_hp = red_tower_1.max_hp
    red_tower_1.brain.set_state("tower_state")
    world.add_entity(red_tower_1)

    red_tower_2 = Tower(world, red_tower_image, red_rock_image)
    red_tower_2.position = Vector2(910, 570)
    red_tower_2.team_id = 1
    red_tower_2.max_hp = TOWER_MAX_HP * RED_MULTIPLIER
    red_tower_2.min_target_distance = TOWER_MIN_TARGET_DISTANCE
    red_tower_2.projectile_range = TOWER_PROJECTILE_RANGE
    red_tower_2.projectile_speed = TOWER_PROJECTILE_SPEED
    red_tower_2.ranged_damage = TOWER_RANGED_DAMAGE * RED_MULTIPLIER
    red_tower_2.ranged_cooldown = TOWER_RANGED_COOLDOWN
    red_tower_2.current_hp = red_tower_2.max_hp
    red_tower_2.brain.set_state("tower_state")
    world.add_entity(red_tower_2)

    red_knight = Knight_TeamB(world, red_knight_image, red_base, Vector2(red_base.spawn_position))
    red_knight.team_id = 1
    red_knight.max_hp = KNIGHT_MAX_HP * RED_MULTIPLIER
    red_knight.maxSpeed = KNIGHT_MAX_SPEED
    red_knight.min_target_distance = KNIGHT_MIN_TARGET_DISTANCE
    red_knight.melee_damage = KNIGHT_MELEE_DAMAGE * RED_MULTIPLIER
    red_knight.melee_cooldown = KNIGHT_MELEE_COOLDOWN
    red_knight.current_hp = red_knight.max_hp
    world.add_entity(red_knight)

    red_archer = Archer_TeamB(world, red_archer_image, red_arrow_image, red_base, Vector2(red_base.spawn_position))
    red_archer.team_id = 1
    red_archer.max_hp = ARCHER_MAX_HP * RED_MULTIPLIER
    red_archer.maxSpeed = ARCHER_MAX_SPEED
    red_archer.min_target_distance = ARCHER_MIN_TARGET_DISTANCE
    red_archer.projectile_range = ARCHER_PROJECTILE_RANGE
    red_archer.projectile_speed = ARCHER_PROJECTILE_SPEED
    red_archer.ranged_damage = ARCHER_RANGED_DAMAGE * RED_MULTIPLIER
    red_archer.ranged_cooldown = ARCHER_RANGED_COOLDOWN
    red_archer.current_hp = red_archer.max_hp
    world.add_entity(red_archer)

    red_wizard = Wizard_TeamB(world, red_wizard_image, red_rock_image, red_base, Vector2(red_base.spawn_position), red_explosion_image)
    red_wizard.team_id = 1
    red_wizard.max_hp = WIZARD_MAX_HP * RED_MULTIPLIER
    red_wizard.maxSpeed = WIZARD_MAX_SPEED
    red_wizard.min_target_distance = WIZARD_MIN_TARGET_DISTANCE
    red_wizard.projectile_range = WIZARD_PROJECTILE_RANGE
    red_wizard.projectile_speed = WIZARD_PROJECTILE_SPEED
    red_wizard.ranged_damage = WIZARD_RANGED_DAMAGE * RED_MULTIPLIER
    red_wizard.ranged_cooldown = WIZARD_RANGED_COOLDOWN
    red_wizard.current_hp = red_wizard.max_hp
    world.add_entity(red_wizard)
    

    # --- Initialize other entities in the world ---
    mountain_1 = Obstacle(world, mountain_image_1)
    mountain_1.position = Vector2(410, 460)
    mountain_1.team_id = 2
    world.add_entity(mountain_1)
    world.obstacles.append(mountain_1)

    mountain_2 = Obstacle(world, mountain_image_2)
    mountain_2.position = Vector2(620, 280)
    mountain_2.team_id = 2
    world.add_entity(mountain_2)
    world.obstacles.append(mountain_2)

    plateau = Obstacle(world, plateau_image)
    plateau.position = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    plateau.team_id = 2
    world.add_entity(plateau)
    world.obstacles.append(plateau)

    grey_tower = Tower(world, grey_tower_image, grey_projectile_image)
    grey_tower.position = Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10)
    grey_tower.team_id = 2
    grey_tower.min_target_distance = GREY_TOWER_MIN_TARGET_DISTANCE
    grey_tower.projectile_range = GREY_TOWER_PROJECTILE_RANGE
    grey_tower.projectile_speed = GREY_TOWER_PROJECTILE_SPEED
    grey_tower.ranged_damage = GREY_TOWER_RANGED_DAMAGE
    grey_tower.ranged_cooldown = GREY_TOWER_RANGED_COOLDOWN
    grey_tower.brain.set_state("tower_state")
    world.add_entity(grey_tower)

    # Splash screen

    if SHOW_SPLASH:
        while True:

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    quit()

            pressed_keys = pygame.key.get_pressed()

            if pressed_keys[K_SPACE]:
                break

            screen.blit(world.background, (0, 0))
            font = pygame.font.SysFont("arial", 60, True)

            title = font.render("Heroes of Ancient Legends", True, (0, 255, 255))
            screen.blit(title, (w//2 - title.get_width()//2, 100))
            team1 = font.render(TEAM_NAME[0] + " (blue)", True, (0, 0, 255))
            screen.blit(team1, (w//2 - team1.get_width()//2, 200))
            vs = font.render("vs.", True, (0, 255, 255))
            screen.blit(vs, (w//2 - vs.get_width()//2, 300))
            team2 = font.render(TEAM_NAME[1] + " (red)", True, (255, 0, 0))
            screen.blit(team2, (w//2 - team2.get_width()//2, 400))

            pygame.display.update()

    clock = pygame.time.Clock()
    while True:

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                quit()

            if pygame.mouse.get_pressed()[0]:
                print(pygame.mouse.get_pos())

        # check for end of game
        if not world.game_end:
            time_passed = clock.tick(30)
            world.process(time_passed)

        world.render(screen)
        
        pygame.display.update()
        

if __name__ == "__main__":
    run()




        
        




        
