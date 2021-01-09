import enum
from typing import List, Dict
from pygame.math import *

from Graph import *
from Character import *

# TODO : These get_{} methods need to accomodate for different teams
TOP_PATH = 0
BOT_PATH = 1
MID_TOP_PATH = 2
MID_BOT_PATH = 3

class Lane(enum.Enum):
    Top = 1
    Mid = 2
    Bot = 3

# TODO : Mid lanes can be split into mid-left, mid-right?
def get_lane(node_id:int) -> Lane:
    top_lanes = [2, 3, 4]
    mid_lanes = [8, 9, 10, 11, 12, 13]
    bot_lanes = [5, 6, 7]

    if node_id in top_lanes:
        return Lane.Top
    elif node_id in mid_lanes:
        return Lane.Mid
    else:
        return Lane.Bot

def get_node_from_id(paths: List[Graph], node_id: int) -> Node:
    graph: Graph
    for graph in paths:
        if node_id in graph.nodes:
            return graph.nodes[node_id]
    return None

def get_lane_character(paths: List[Graph], person: Character) -> Lane:
    return get_lane(get_nearest_node(paths, person.position))

# TODO : Mid_top and Mid_bot separation
def get_graph(person: Character, lane: Lane) -> Graph:
    if Lane(lane) == Lane.Top:
        return get_top_graph(person)
    elif Lane(lane) == Lane.Mid:
        return get_mid_top_graph(person)
    elif Lane(lane) == Lane.Bot:
        return get_bot_graph(person)

def get_top_graph(person: Character) -> Graph:
    return person.world.paths[TOP_PATH]

def get_mid_top_graph(person: Character) -> Graph:
    return person.world.paths[MID_TOP_PATH]

def get_mid_bot_graph(person: Character) -> Graph:
    return person.world.paths[MID_BOT_PATH]

def get_bot_graph(person: Character) -> Graph:
    return person.world.paths[BOT_PATH]

def get_path_to_enemy_base(person:Character, path_graph: Graph, position: Vector2) -> List[NodeRecord]:
    # TODO : use person to check team, currently set to 4 (red base)
    return pathFindAStar(
        path_graph, 
        path_graph.get_nearest_node(position), 
        get_node_from_id(person.world.paths, 4)
    )

# def get_path_to_my_base(person: Character, path_graph: Graph, position: Vector2) -> List[NodeRecord]:
#     return pathFindAStar(
#         path_graph,
#         path_graph.get_nearest_node(position), 
#         get_node_from_id(person.world.paths, 0)
#     )

# The reason why this is needed is because the get_nearest_node() implemented
# is a method, not a function, and it cannot be used without states
def get_nearest_node(paths: List[Graph], position: Vector2) -> Node:
    nearest = None
    nearest_distance = inf

    # Typehints
    graph:Graph
    node:Node

    for graph in paths:
        for node in graph.nodes.values():
            distance = (position - Vector2(node.position)).length()
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = node
    return nearest


# returns {int1: int2}
# int1: index of self.world.paths
# int2: count of enemies in that path
# usage: get_enemies_positions_in_lanes(self.{character}.world.paths, self.{character})
def get_enemies_positions_in_lanes(
    paths: List[Graph], person: Character
) -> Dict[int, int]:
    # Set default values for the lanes
    enemy_positions_in_lane:Dict[Lane, int] = {}
    for lane in Lane:
        enemy_positions_in_lane[lane] = 0

    enemy_positions:List[int] = []

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

        node = get_nearest_node(paths, entity.position)
        enemy_positions.append(node.id)
    
    for node_id in enemy_positions:
        enemy_positions_in_lane[get_lane(node_id)] += 1
    
    for key, value in enemy_positions_in_lane.items():
        print(Lane(key), " ", value)
    
    return enemy_positions_in_lane