import enum
from typing import List, Dict
from pygame.math import *

from Graph import *
from Character import *

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
    
    return enemy_positions