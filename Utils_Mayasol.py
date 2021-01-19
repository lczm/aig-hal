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

MAIN_CHARACTER_SCORE: int = 4
CHARACTER_SCORING: Dict[str, int] = {
    "knight": MAIN_CHARACTER_SCORE,
    "archer": MAIN_CHARACTER_SCORE,
    "wizard": MAIN_CHARACTER_SCORE,
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
    return person.world.paths[TOP_PATH]


def get_mid_top_graph(person: Character) -> Graph:
    return person.world.paths[MID_TOP_PATH]


def get_mid_bot_graph(person: Character) -> Graph:
    return person.world.paths[MID_BOT_PATH]


def get_bot_graph(person: Character) -> Graph:
    return person.world.paths[BOT_PATH]


def get_path_to_enemy_base(person: Character, path_graph: Graph, position: Vector2) -> List[Connection]:
    return pathFindAStar(
        path_graph,
        path_graph.get_nearest_node(position),
        get_node_from_id(person.world.paths, person.base.target_node_index)
    )


def get_path_to_enemy_base_from_my_base(person: Character, path_graph: Graph) -> List[Connection]:
    return pathFindAStar(
        path_graph,
        get_initial_start_node(person),
        get_node_from_id(person.world.paths, person.base.target_node_index)
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
    nearest = None
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

# just get nearest opponent but projectile


def get_nearest_projectile(person: Character) -> GameEntity:

    nearest_projectile = None
    distance = 0.

    for entity in person.world.entities.values():
        # neutral entity
        if entity.team_id == 2:
            continue

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
            
        # there is an entity, it is either my team or the opponent's
        # get closest node for this entity
        node: Node = get_nearest_node_global(paths, entity.position)
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
        relative_threat[lane] = my_positions_in_lane[lane] - enemy_positions_in_lane[lane]

    return relative_threat


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
    

# Debug function to see where the character is going from/to
def draw_circle_at_position(position: Vector2, surface: pygame.Surface,
                            color: Tuple[int] = (255, 0, 0)) -> None:
    pygame.draw.circle(surface, color, position, 15)
    return None


def generate_pathfinding_graphs(
    filename: str, person: Character
) -> List[Graph]:

    graph: Graph = Graph(person.world)
    file = open(filename, "r")

    # Create the nodes
    line = file.readline()
    while line != "connections\n":
        data = line.split()
        graph.nodes[int(data[0])] = Node(graph, int(data[0]), int(data[1]), int(data[2]))
        line = file.readline()
    
    # Create the connections
    line = file.readline()
    while line != "paths\n":
        data = line.split()
        node0 = int(data[0])
        node1 = int(data[1])
        distance = (Vector2(graph.nodes[node0].position) - Vector2(graph.nodes[node1].position)).length()
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
            path.nodes[int(data[i])] = Node(path, int(data[i]), node.position[0], node.position[1])

        # Create the connections
        for i in range(0, len(data)-1):
            node0 = int(data[i])
            node1 = int(data[i + 1])
            distance = (Vector2(graph.nodes[node0].position) - Vector2(graph.nodes[node1].position)).length()
            path.nodes[node0].addConnection(path.nodes[node1], distance)
            path.nodes[node1].addConnection(path.nodes[node0], distance)
            
        paths.append(path)
        line = file.readline()
    
    return paths