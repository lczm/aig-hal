import pygame
from pygame.math import *

class Graph(object):

    def __init__(self, world):

        self.world = world

        self.connections = []           # an unordered list of connections
        self.nodes = {}                 # dictionary of nodes, indexed by node.id


    # returns the connections of from-node as an unordered list
    def getConnections(self, fromNode):

        cons = []
        for con in self.connections:
            if con.fromNode.id == fromNode.id:
                cons.append(con)
                
        return cons
    

    # adds a connection
    def addConnection(self, fromNode, toNode, cost):

        connection = Connection(self, cost, fromNode, toNode)
        self.connections.append(connection)


    # returns True if this connection exists, False otherwise
    def hasConnection(self, fromNode, toNode):
        for con in self.connections:
            if con.fromNode.id == fromNode.id and con.toNode.id == toNode.id:
                return True

        return False
    

    def render(self, surface):

        # draw the connections
        for con in self.connections:
            pygame.draw.line(surface, (100, 255, 0), con.fromNode.position, con.toNode.position)

        # draw the nodes
        for nodeKey in self.nodes:
            pygame.draw.circle(surface, (200, 255, 0), self.nodes[nodeKey].position, 5)


    # --- returns nearest node to given position ---
    def get_nearest_node(self, position):

        nearest = None
        for node in self.nodes.values():
            if nearest is None:
                nearest = node
                nearest_distance = (position - Vector2(nearest.position)).length()
            else:
                distance = (position - Vector2(node.position)).length()
                if distance < nearest_distance:
                    nearest = node
                    nearest_distance = distance

        return nearest
            
            
class Connection(object):

    def __init__(self, graph, cost, fromNode, toNode):

        self.graph = graph
        self.cost = cost
        self.fromNode = fromNode
        self.toNode = toNode


class Node(object):

    def __init__(self, graph, id, x, y):
        
        self.id = id
        self.graph = graph
        self.position = (x, y)
        self.connections = []
        
    # add a directed connection to toNode
    def addConnection(self, toNode, cost):

        connection = Connection(self.graph, cost, self, toNode)
        self.connections.append(connection)
        self.graph.connections.append(connection)


class NodeRecord:

    def __init__(self, node, connection, costSoFar, estimatedCost = 0):
        self.node = node
        self.connection = connection
        self.costSoFar = costSoFar
        self.estimatedCost = estimatedCost


def heuristic(graph, node, end):

    return (Vector2(end.position) - Vector2(node.position)).length()


def pathFindAStar(graph, start, end):

    startRecord = NodeRecord(start, None, 0, heuristic(graph, start, end))
    openList = {}
    openList[startRecord.node.id] = startRecord
    closedList = {}

    while openList:

        # get smallest element in open list
        current = min(openList.items(), key = lambda record : record[1].estimatedCost)[1]

        del openList[current.node.id]

        if current.node.id == end.id:
            break

        connections = graph.getConnections(current.node)

        for con in connections:
            endNode = con.toNode
            endNodeCost = current.costSoFar + con.cost

            if endNode.id in closedList.keys():
                continue

            elif endNode.id in openList.keys():                
                if openList[endNode.id].costSoFar > endNodeCost:
                    openList[endNode.id].costSoFar = endNodeCost
                    openList[endNode.id].connection = con
                    openList[endNode.id].estimatedCost = endNodeCost + heuristic(graph, endNode, end)

            else:
                openList[endNode.id] = NodeRecord(endNode, con, endNodeCost, endNodeCost + heuristic(graph, endNode, end))

        closedList[current.node.id] = current


    if current.node.id != end.id:
        return None

    else:
        path = []

        while current.node.id != start.id:
            path.append(current.connection)
            current = closedList[current.connection.fromNode.id]

        path.reverse()

    return path
