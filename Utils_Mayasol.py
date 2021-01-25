import enum
from typing import List, Dict, Tuple
from pygame.math import *

from Graph import *
from Character import *

# TODO : These get_{} methods need to accomodate for different teams
TOP_PATH = 0
BOT_PATH = 1
MID_TOP_PATH = 2
MID_BOT_PATH = 3

KNIGHT_SCORE: int = 4
ARCHER_SCORE: int = 4
WIZARD_SCORE: int = 6
CHARACTER_SCORING: Dict[str, int] = {
    "knight": KNIGHT_SCORE,
    "archer": ARCHER_SCORE,
    "wizard": WIZARD_SCORE,
    "orc": 1,
}


class Lane(enum.Enum):
    Top = 1
    Mid = 2
    Bot = 3
    Base = 4

# TODO : Mid lanes can be split into mid-left, mid-right?


def get_character_score(person: Character) -> int:
    return CHARACTER_SCORING.get(person.name, 1)


def get_lane(node_id: int) -> Lane:
    top_lanes = [2, 3, 4, 14, 15, 16, 17, 18, 19, 20, 21]
    mid_lanes = [8, 9, 10, 11, 12, 13]
    bot_lanes = [5, 6, 7, 22, 23, 24, 25, 26, 27, 28]

    if node_id in top_lanes:
        return Lane.Top
    elif node_id in mid_lanes:
        return Lane.Mid
    elif node_id in bot_lanes:
        return Lane.Bot
    else:
        return Lane.Base


def get_node_from_id(paths: List[Graph], node_id: int) -> Node:
    graph: Graph
    for graph in paths:
        if node_id in graph.nodes:
            return graph.nodes[node_id]
    return None


def get_initial_start_node(person: Character) -> Node:
    # This does not need to use person.paths as the
    # node ids are identical between the default path
    # and the modified paths
    if person.team_id == 0:   # Blue team
        return get_node_from_id(person.world.paths, 0)
    elif person.team_id == 1:  # Red  team
        return get_node_from_id(person.world.paths, 4)
    else:  # Neutral... or some others
        return None


def get_lane_character(graph: Graph, person: Character) -> Lane:
    return get_lane(get_nearest_node_local(graph, person.position).id)

# TODO : Mid_top and Mid_bot separation


def get_graph(person: Character, graph: Graph, lane: Lane) -> Graph:
    if Lane(lane) == Lane.Top:
        return get_top_graph(person)
    elif Lane(lane) == Lane.Mid:
        return get_mid_top_graph(person)
    elif Lane(lane) == Lane.Bot:
        return get_bot_graph(person)
    else:
        return graph


def get_top_graph(person: Character) -> Graph:
    if hasattr(person, "paths"):
        return person.paths[TOP_PATH]
    else:
        return person.world.paths[TOP_PATH]


def get_mid_top_graph(person: Character) -> Graph:
    if hasattr(person, "paths"):
        return person.paths[MID_TOP_PATH]
    else:
        return person.world.paths[MID_TOP_PATH]


def get_mid_bot_graph(person: Character) -> Graph:
    if hasattr(person, "paths"):
        return person.paths[MID_BOT_PATH]
    else:
        return person.world.paths[MID_BOT_PATH]


def get_bot_graph(person: Character) -> Graph:
    if hasattr(person, "paths"):
        return person.paths[BOT_PATH]
    else:
        return person.world.paths[BOT_PATH]


def get_path_to_enemy_base(person: Character, path_graph: Graph, position: Vector2) -> List[Connection]:
    paths: List[Graph]
    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    return pathFindAStar(
        path_graph,
        path_graph.get_nearest_node(position),
        get_node_from_id(paths, person.base.target_node_index)
    )


def get_path_to_enemy_base_from_my_base(person: Character, path_graph: Graph) -> List[Connection]:
    paths: List[Graph]
    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    return pathFindAStar(
        path_graph,
        get_initial_start_node(person),
        get_node_from_id(paths, person.base.target_node_index)
    )


def get_path_to_my_base(person: Character, path_graph: Graph, position: Vector2) -> List[Connection]:
    paths: List[Graph]
    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    return pathFindAStar(
        path_graph,
        path_graph.get_nearest_node(position),
        get_node_from_id(paths, person.base.spawn_node_index)
    )


def get_path_from_base_to_position(person: Character, path_graph: Graph) -> List[Connection]:
    paths: List[Graph]
    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    return pathFindAStar(
        path_graph,
        get_initial_start_node(person),
        get_nearest_node_global_ignoring_base(paths, person.position)
    )


# def get_path_to_my_base(person: Character, path_graph: Graph, position: Vector2) -> List[NodeRecord]:
#     return pathFindAStar(
#         path_graph,
#         path_graph.get_nearest_node(position),
#         get_node_from_id(person.world.paths, 0)
#     )


def get_nearest_node_local(graph: Graph, position: Vector2) -> Node:
    nearest = None
    nearest_distance = inf

    # Typehints
    node: Node
    for node in graph.nodes.values():
        distance = (position - Vector2(node.position)).length()
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = node
    return nearest


# The reason why this is needed is because the get_nearest_node() implemented
# is a method, not a function, and it cannot be used without states
def get_nearest_node_global(paths: List[Graph], position: Vector2) -> Node:
    nearest: Node = None
    nearest_distance = inf

    # Typehints
    graph: Graph
    node: Node
    for graph in paths:
        for node in graph.nodes.values():
            distance = (position - Vector2(node.position)).length()
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = node
    return nearest


def get_nearest_node_global_ignoring_base(paths: List[Graph], position: Vector2) -> Node:
    nearest: Node = None
    nearest_distance: float = inf

    graph: Graph
    node: Node
    for graph in paths:
        for node in graph.nodes.values():
            if get_lane(node.id) == Lane.Base:
                continue
            distance = (position - Vector2(node.position)).length()
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = node

    return nearest


# just get nearest opponent but projectile
def get_nearest_projectile(person: Character) -> GameEntity:

    nearest_projectile = None
    distance = 0.

    for entity in person.world.entities.values():
        # same team
        if entity.team_id == person.team_id:
            continue

        if entity.name != "projectile" and entity.name != "explosion":
            continue

        if nearest_projectile is None:
            nearest_projectile = entity
            distance = (person.position - entity.position).length()
        else:
            if distance > (person.position - entity.position).length():
                distance = (person.position - entity.position).length()
                nearest_projectile = entity

    return nearest_projectile


def check_for_obstacles(rect: Rect, obstacle_list: List) -> bool:
    for obstacle in obstacle_list:
        if rect.colliderect(obstacle.rect):
            return True
    return False


def check_screen_edge(position: Vector2) -> bool:
    if position[0] < 0 or position[0] > SCREEN_WIDTH or \
            position[1] < 0 or position[1] > SCREEN_HEIGHT:
        return True
    return False


# returns {int1: int2}
# int1: index of self.world.paths
# int2: count of enemies in that path
# usage: get_enemies_positions_in_lanes(self.{character}.world.paths, self.{character})
def get_enemies_positions_in_lanes(
    paths: List[Graph], person: Character
) -> Dict[int, int]:
    # Set default values for the lanes
    enemy_positions_in_lane: Dict[Lane, int] = {}
    for lane in Lane:
        enemy_positions_in_lane[lane] = 0

    enemy_positions: List[int] = []

    # Typehint entity before looping over them
    entity: Character
    for entity in person.world.entities.values():
        # neutral entity can be ignored
        if entity.team_id == 2:
            continue
        # same team entities can be ignored
        if entity.team_id == person.team_id:
            continue
        # projectiles and explosions can be ignored
        if entity.name == "projectile" or entity.name == "explosion":
            continue
        # entities that are ko-ed can be ignored
        if entity.ko:
            continue
        # ignore the tower and base as well
        if entity.name == "base" or entity.name == "tower":
            continue

        # node = get_nearest_node_global(paths, entity.position)
        node = get_nearest_node_global(paths, entity.move_target.position)
        enemy_positions.append(node.id)

    for node_id in enemy_positions:
        #with character scoring
        enemy_positions_in_lane[get_lane(node_id)] += 1

    return enemy_positions_in_lane


def get_relative_lane_threat(
    paths: List[Graph], person: Character
) -> Dict[Lane, int]:
    my_positions_in_lane: Dict[Lane, int] = {}
    enemy_positions_in_lane: Dict[Lane, int] = {}

    # Set every lane to 0 threat
    for lane in Lane:
        my_positions_in_lane[lane] = 0
        enemy_positions_in_lane[lane] = 0

    entity: Character
    for entity in person.world.entities.values():
        # neutral entity
        if entity.team_id == 2:
            continue
        # projectiles and explosions can be ignored
        if entity.name == "projectile" or entity.name == "explosion":
            continue
        # ko-ed can be ignored
        if entity.ko:
            continue
        # bases and towers can be ignored
        if entity.name == "base" or entity.name == "tower":
            continue

        # Dont count 'myself' into the calculations
        if entity.id == person.id:
            continue

        # there is an entity, it is either my team or the opponent's
        # get closest node for this entity
        node: Node = get_nearest_node_global_ignoring_base(
            paths, entity.position)
        lane: Lane = get_lane(node.id)

        # If entity is at lane, ignore
        if lane == Lane.Base:
            continue

        # my team
        if entity.team_id == person.team_id:
            my_positions_in_lane[lane] += get_character_score(entity)
        else:
            enemy_positions_in_lane[lane] += get_character_score(entity)

    # Get the difference between the node
    relative_threat: Dict[Lane, int] = {}
    for lane in Lane:
        relative_threat[lane] = my_positions_in_lane[lane] - \
            enemy_positions_in_lane[lane]

    return relative_threat

def lane_threat(
    paths: List[Graph], person: Character
) -> Dict[Lane, int]:
    enemy_positions_in_lane: Dict[Lane, int] = {}

    # Set every lane to 0 threat
    for lane in Lane:
        enemy_positions_in_lane[lane] = 0

    entity: Character
    for entity in person.world.entities.values():
        # neutral entity
        if entity.team_id == 2:
            continue
        # projectiles and explosions can be ignored
        if entity.name == "projectile" or entity.name == "explosion":
            continue
        # ko-ed can be ignored
        if entity.ko:
            continue
        # bases and towers can be ignored
        if entity.name == "base" or entity.name == "tower":
            continue

        # Dont count 'myself' into the calculations
        if entity.id == person.id:
            continue

        # there is an entity, it is either my team or the opponent's
        # get closest node for this entity
        node: Node = get_nearest_node_global_ignoring_base(
            paths, entity.position)
        lane: Lane = get_lane(node.id)

        # If entity is at lane, ignore
        if lane == Lane.Base:
            continue

        # enemy team
        if entity.team_id == 1 - person.team_id:
            enemy_positions_in_lane[lane] += get_character_score(entity)

    return enemy_positions_in_lane


def get_highest_lane_threat(
    paths: List[Graph], person: Character
) -> Lane:
    relative_threat: Dict[Lane, int] = get_relative_lane_threat(paths, person)

    highest_lane: Lane = None
    # 'Highest' because it should also be negative threat is
    # most dangerous, my team (threat) - opponent team (threat)
    highest_threat = inf

    for lane in Lane:
        threat = relative_threat[lane]
        if threat < highest_threat:
            highest_lane = lane
            highest_threat = threat

    print(relative_threat)
    print("Highest : ", highest_lane, highest_threat)

    return highest_lane


def generate_pathfinding_graphs(
    filename: str, person: Character
) -> List[Graph]:

    graph: Graph = Graph(person.world)
    file = open(filename, "r")

    # Create the nodes
    line = file.readline()
    while line != "connections\n":
        data = line.split()
        graph.nodes[int(data[0])] = Node(
            graph, int(data[0]), int(data[1]), int(data[2]))
        line = file.readline()

    # Create the connections
    line = file.readline()
    while line != "paths\n":
        data = line.split()
        node0 = int(data[0])
        node1 = int(data[1])
        distance = (Vector2(graph.nodes[node0].position) -
                    Vector2(graph.nodes[node1].position)).length()
        graph.nodes[node0].addConnection(graph.nodes[node1], distance)
        graph.nodes[node1].addConnection(graph.nodes[node0], distance)
        line = file.readline()

    # Create the paths
    paths = []
    line = file.readline()
    while line != "":
        path = Graph(person.world)
        data = line.split()

        # Create the nodes
        for i in range(0, len(data)):
            node = graph.nodes[int(data[i])]
            path.nodes[int(data[i])] = Node(path, int(data[i]),
                                            node.position[0], node.position[1])

        # Create the connections
        for i in range(0, len(data)-1):
            node0 = int(data[i])
            node1 = int(data[i + 1])
            distance = (Vector2(
                graph.nodes[node0].position) - Vector2(graph.nodes[node1].position)).length()
            path.nodes[node0].addConnection(path.nodes[node1], distance)
            path.nodes[node1].addConnection(path.nodes[node0], distance)

        paths.append(path)
        line = file.readline()

    return paths


def generate_series_of_connections(person: Character, node_ids: List[int]) -> List[Connection]:
    connections: List[Connection] = []

    # Use path graph in the person if it exists
    paths: List[Graph]
    path_graph: Graph

    if hasattr(person, "path_graph"):
        path_graph = person.path_graph
    else:
        path_graph = person.world.path_graph

    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    for i in range(len(node_ids) - 1):
        connections.append(Connection(
            graph=path_graph, cost=0,
            fromNode=get_node_from_id(paths, node_ids[i]),
            toNode=get_node_from_id(paths, node_ids[i+1])
        ))

    return connections


# This gets an opponent that is within range while being relatively sane,
# i.e. picks targets that are one shot away
def get_opponent_in_range(person: Character) -> Character:
    nearest_opponent: Character = None
    distance: float = 0

    range: float = person.min_target_distance
    attack_damage: float = person.ranged_damage

    entity: Character
    for entity in person.world.entities.values():
        # neutral entity
        if entity.team_id == 2:
            continue
        # same team
        if entity.team_id == person.team_id:
            continue
        # projectile or explosion
        if entity.name == "projectile" or entity.name == "explosion":
            continue
        # dead
        if entity.ko:
            continue

        # Get the distance away from the entity
        current_distance: float = (person.position - entity.position).length()

        # # If the entity is within attackable range
        # if current_distance <= range:
        #     # If the entity is 1 shot away from dying, just select that.
        #     if entity.current_hp <= attack_damage:
        #         return entity
        #     else:
        #         if nearest_opponent is None:
        #             nearest_opponent = entity
        #             distance = current_distance
        #         else:
        #             if distance > current_distance:
        #                 distance = current_distance
        #                 nearest_opponent = entity

        if nearest_opponent is None:
            nearest_opponent = entity
            distance = current_distance
        else:
            if distance > current_distance:
                distance = current_distance
                nearest_opponent = entity

    # Get the distance between them,
    # if the distance between them is below a certain threshold
    # there is no point in switching targets
    # Given a situation where 
    # me ------  a
    #            b
    # where the distance between a and b is very little
    # and i am already shooting at one of them, and the distance is
    # too short to care, there is no point to switch targets
    # if person.target is not None and nearest_opponent is not None:
    #     if nearest_opponent.id != person.target.id:
    #         if (nearest_opponent.position - person.target.position).length() < 15:
    #             return person.target

    return nearest_opponent


def get_amount_of_enemies_in_range(person: Character, range: float):
    amount: int = 0

    entity: Character
    for entity in person.world.entities.values():
        # neutral entity
        if entity.team_id == 2:
            continue
        # same team
        if entity.team_id == person.team_id:
            continue
        # projectile or explosion
        if entity.name == "projectile" or entity.name == "explosion":
            continue
        # dead
        if entity.ko:
            continue

        # Get the distance away from the entity
        current_distance: float = (person.position - entity.position).length()
        if current_distance <= range:
            amount += 1

    return amount


def get_amount_of_enemies_in_range_by_score(person: Character, range: float) -> Dict[Lane, int]:
    enemy_positions_in_lane: Dict[Lane, int] = {}

    paths: List[Graph]
    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    entity: Character
    for entity in person.world.entities.values():
        # neutral entity
        if entity.team_id == 2:
            continue
        # same team
        if entity.team_id == person.team_id:
            continue
        # projectile or explosion
        if entity.name == "projectile" or entity.name == "explosion":
            continue
        # dead
        if entity.ko:
            continue

        # Get the distance away from the entity
        current_distance: float = (person.position - entity.position).length()
        if current_distance <= range:
            enemy_lane: Lane = get_lane(get_nearest_node_global(paths))
            enemy_positions_in_lane[enemy_lane] += get_character_score(entity)

    return enemy_positions_in_lane

def get_current_connection_at_position_to_node(person: Character) -> int:
    paths: List[Graph]
    if hasattr(person, "paths"):
        paths = person.paths
    else:
        paths = person.world.paths

    nearest_node = get_nearest_node_global(paths, person.position)

    for i in range(len(person.path)):
        if person.path[i].toNode.id == nearest_node.id:
            return i

    return 0


# Debug function to see where the character is going from/to
def draw_circle_at_position(position: Vector2, surface: pygame.Surface,
                            color: Tuple[int] = (255, 0, 0)) -> None:
    pygame.draw.circle(surface, color, position, 15)
    return None


def dodge_projectile(person: Character, explosion_dodge_backward: bool = True):
    nearest_projectile: GameEntity = get_nearest_projectile(person)
    if nearest_projectile is not None and not nearest_projectile.name == "explosion":
        distance_from_origin: Vector2 = nearest_projectile.position - \
            nearest_projectile.origin_position
        distance_until_despawn: float = nearest_projectile.max_range - \
            distance_from_origin.length()
        original_velocity: Vector2 = nearest_projectile.velocity / nearest_projectile.maxSpeed
        # normal projectile
        if not nearest_projectile.explosive_image:
            # +2 to account for error when converting float to int
            for i in range(int(distance_until_despawn + 2)):
                projectile_rect: Rect = nearest_projectile.rect.copy()
                w, h = nearest_projectile.image.get_size()
                projectile_rect.x = nearest_projectile.position.x + \
                    (original_velocity.x * i) - w/2
                projectile_rect.y = nearest_projectile.position.y + \
                    (original_velocity.y * i) - h/2
                if (projectile_rect.colliderect(person.rect)):
                    person.projectile_rect = projectile_rect
                    distance_until_collide: float = nearest_projectile.position.length(
                    ) - Vector2(projectile_rect.x, projectile_rect.y).length()
                    # rotate velocity 90 degree clockwise from projectile
                    projectile_velocity = Vector2(
                        nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                    y_velocity = projectile_velocity.y
                    projectile_velocity.x *= -1
                    projectile_velocity.y = projectile_velocity.x
                    projectile_velocity.x = y_velocity
                    fake_velocity = Vector2(
                        projectile_velocity.x, projectile_velocity.y)
                    fake_rect = person.rect.copy()
                    w, h = person.image.get_size()
                    character_original_velocity = fake_velocity / person.maxSpeed

                    for j in range(int(distance_until_collide)):
                        fake_rect.x = person.position.x + \
                            (character_original_velocity.x * j) - w/2
                        fake_rect.y = person.position.y + \
                            (character_original_velocity.y * j) - h/2
                        fake_rect_position = Vector2(
                            fake_rect.x, fake_rect.y)
                        # if possible to dodge
                        if not (projectile_rect.colliderect(fake_rect)) \
                                and not check_for_obstacles(fake_rect, person.world.obstacles) \
                                and not check_screen_edge(fake_rect_position):
                            # dodge 90 degree clockwise from the projectile
                            person.velocity = fake_rect_position - person.position
                            person.velocity.normalize_ip()
                            person.velocity *= person.maxSpeed
                            return

                    # if code reaches here means cant dodge 90 degree clockwise
                    projectile_velocity = Vector2(
                        nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                    x_velocity = projectile_velocity.x
                    projectile_velocity.y *= -1
                    projectile_velocity.x = projectile_velocity.y
                    projectile_velocity.y = x_velocity
                    fake_velocity = Vector2(
                        projectile_velocity.x, projectile_velocity.y)
                    fake_rect = person.rect.copy()
                    character_original_velocity = fake_velocity / person.maxSpeed
                    for k in range(int(distance_until_collide)):
                        fake_rect.x = person.position.x + \
                            (character_original_velocity.x * k) - w/2
                        fake_rect.y = person.position.y + \
                            (character_original_velocity.y * k) - h/2
                        fake_rect_position = Vector2(
                            fake_rect.x, fake_rect.y)
                        # if possible to dodge
                        if not (projectile_rect.colliderect(fake_rect)) \
                                and not check_for_obstacles(fake_rect, person.world.obstacles) \
                                and not check_screen_edge(fake_rect_position):
                            # dodge 90 degree counterclockwise from the projectile
                            person.velocity = fake_rect_position - person.position
                            person.velocity.normalize_ip()
                            person.velocity *= person.maxSpeed
                            return

                    print("undodgeable")

        # explosive projectile
        else:
            point_of_explosion: Vector2 = nearest_projectile.position + \
                (original_velocity
                    * distance_until_despawn)
            # create a explosion object that isnt in the game so that i can see if it collides with the character
            explosion = Explosion(nearest_projectile.owner, nearest_projectile.owner.world, nearest_projectile.explosive_image,
                                  1000, point_of_explosion, nearest_projectile.owner.team_id)
            # set the x and y coordinate of the explosion (for some reason doesnt set it automatically)
            w, h = explosion.image.get_size()
            explosion.rect.x = point_of_explosion.x - w/2
            explosion.rect.y = point_of_explosion.y - h/2
            collide_list = pygame.sprite.spritecollide(
                explosion, person.world.entities.values(), False)
            explosion_position = Vector2(
                explosion.rect.x, explosion.rect.y)
            distance_until_explode = point_of_explosion.length() - explosion_position.length()
            if person in collide_list:
                projectile_velocity = Vector2(
                    nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                y_velocity = projectile_velocity.y
                projectile_velocity.x *= -1
                projectile_velocity.y = projectile_velocity.x
                projectile_velocity.x = y_velocity
                fake_velocity = Vector2(
                    projectile_velocity.x, projectile_velocity.y)
                fake_rect = person.rect.copy()
                w, h = person.image.get_size()
                character_original_velocity = fake_velocity / person.maxSpeed
                for i in range(int(distance_until_explode)):
                    fake_rect.x = person.position.x + \
                        (character_original_velocity.x * i) - w/2
                    fake_rect.y = person.position.y + \
                        (character_original_velocity.y * i) - h/2
                    fake_rect_position = Vector2(
                        fake_rect.x, fake_rect.y)
                    # if possible to dodge
                    if not (explosion.rect.colliderect(fake_rect)) \
                            and not check_for_obstacles(fake_rect, person.world.obstacles) \
                            and not check_screen_edge(fake_rect_position):
                        # dodge 90 degree clockwise from the projectile
                        #person.velocity.x *= -1
                        #person.velocity.y = person.velocity.x
                        #person.velocity.x = y_velocity
                        person.velocity = fake_rect_position - person.position
                        person.velocity.normalize_ip()
                        person.velocity *= person.maxSpeed
                        return
                projectile_velocity = Vector2(
                    nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                x_velocity = projectile_velocity.x
                projectile_velocity.y *= -1
                projectile_velocity.x = projectile_velocity.y
                projectile_velocity.y = x_velocity
                fake_velocity = Vector2(
                    projectile_velocity.x, projectile_velocity.y)
                fake_rect = person.rect.copy()
                character_original_velocity = fake_velocity / person.maxSpeed
                for j in range(int(distance_until_explode)):
                    fake_rect.x = person.position.x + \
                        (character_original_velocity.x * j) - w/2
                    fake_rect.y = person.position.y + \
                        (character_original_velocity.y * j) - h/2
                    fake_rect_position = Vector2(
                        fake_rect.x, fake_rect.y)
                    # if possible to dodge
                    if not (explosion.rect.colliderect(fake_rect)) \
                            and not check_for_obstacles(fake_rect, person.world.obstacles) \
                            and not check_screen_edge(fake_rect_position):
                        # dodge 90 degree clockwise from the projectile
                        #person.velocity.x *= -1
                        #person.velocity.y = person.velocity.x
                        #person.velocity.x = y_velocity
                        person.velocity = fake_rect_position - person.position
                        person.velocity.normalize_ip()
                        person.velocity *= person.maxSpeed
                        return
                if (explosion_dodge_backward):
                    projectile_velocity = Vector2(
                        nearest_projectile.velocity.x, nearest_projectile.velocity.y)
                    x_velocity = projectile_velocity.x
                    fake_velocity = Vector2(
                        projectile_velocity.x, projectile_velocity.y)
                    fake_rect = person.rect.copy()
                    character_original_velocity = fake_velocity / person.maxSpeed
                    for k in range(int(distance_until_explode)):
                        fake_rect.x = person.position.x + \
                            (character_original_velocity.x * k) - w/2
                        fake_rect.y = person.position.y + \
                            (character_original_velocity.y * k) - h/2
                        fake_rect_position = Vector2(
                            fake_rect.x, fake_rect.y)
                        # if possible to dodge
                        if not (explosion.rect.colliderect(fake_rect)) \
                                and not check_for_obstacles(fake_rect, person.world.obstacles) \
                                and not check_screen_edge(fake_rect_position):
                            # dodge 90 degree clockwise from the projectile
                            #person.velocity.x *= -1
                            #person.velocity.y = person.velocity.x
                            #person.velocity.x = y_velocity
                            person.velocity = fake_rect_position - person.position
                            person.velocity.normalize_ip()
                            person.velocity *= person.maxSpeed
                            return
    # elif nearest_projectile is not None and nearest_projectile.name == "explosion":
    #     point_of_explosion: Vector2 = Vector2(
    #         nearest_projectile.position.x, nearest_projectile.position.y)
    #     explosion_rect = nearest_projectile.rect.copy()
    #     predicted_character_rect = person.rect.copy()
    #     predicted_character_rect.x += person.velocity.x * person.time_passed
    #     predicted_character_rect.y += person.velocity.y * person.time_passed
    #     if (explosion_rect.colliderect(predicted_character_rect)):
    #         person.velocity = -person.velocity
