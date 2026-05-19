from dstar.priority_queue import PriorityQueue, Priority
from dstar.grid import OccupancyGridMap
import numpy as np
from dstar.utils import heuristic, Vertex, Vertices
from typing import Dict, List, Tuple

OBSTACLE = 255
UNOCCUPIED = 0


class DStarLite:
    def __init__(self, map: OccupancyGridMap, s_start: (int, int), s_goal: (int, int)):
        """
        :param map: the ground truth map of the environment provided by gui
        :param s_start: start location
        :param s_goal: end location
        """
        self.new_edges_and_old_costs = None

        # algorithm start
        self.s_start = s_start
        self.s_goal = s_goal
        self.s_last = s_start
        self.k_m = 0  # accumulation
        self.U = PriorityQueue()
        self.rhs = np.ones((map.x_dim, map.y_dim)) * np.inf
        self.g = self.rhs.copy()

        self.sensed_map = OccupancyGridMap(x_dim=map.x_dim,
                                           y_dim=map.y_dim,
                                           exploration_setting='8N')
        # Copy the weight map from the input map
        self.sensed_map.weight_map = map.weight_map.copy()

        self.rhs[self.s_goal] = 0
        self.U.insert(self.s_goal, Priority(heuristic(self.s_start, self.s_goal), 0))

    def calculate_key(self, s: (int, int)):
        """
        :param s: the vertex we want to calculate key
        :return: Priority class of the two keys
        """
        k1 = min(self.g[s], self.rhs[s]) + heuristic(self.s_start, s) + self.k_m
        k2 = min(self.g[s], self.rhs[s])
        return Priority(k1, k2)

    def c(self, u: Tuple[int, int], v: Tuple[int, int]) -> float:
        """
        Calculate the cost between nodes
        :param u: from vertex
        :param v: to vertex
        :return: weighted distance to traverse. inf if obstacle in path
        """
        if not self.sensed_map.is_unoccupied(u) or not self.sensed_map.is_unoccupied(v):
            return float('inf')
        else:
            u_weight = self.sensed_map.get_weight(u)
            v_weight = self.sensed_map.get_weight(v)
            return heuristic(u, v) * max(u_weight, v_weight)

    def contain(self, u: (int, int)) -> (int, int):
        return u in self.U.vertices_in_heap

    def update_vertex(self, u: (int, int)):
        if self.g[u] != self.rhs[u] and self.contain(u):
            self.U.update(u, self.calculate_key(u))
        elif self.g[u] != self.rhs[u] and not self.contain(u):
            self.U.insert(u, self.calculate_key(u))
        elif self.g[u] == self.rhs[u] and self.contain(u):
            self.U.remove(u)

    def compute_shortest_path(self):
        while self.U.top_key() < self.calculate_key(self.s_start) or self.rhs[self.s_start] > self.g[self.s_start]:
            u = self.U.top()
            k_old = self.U.top_key()
            k_new = self.calculate_key(u)

            if k_old < k_new:
                self.U.update(u, k_new)
            elif self.g[u] > self.rhs[u]:
                self.g[u] = self.rhs[u]
                self.U.remove(u)
                pred = self.sensed_map.succ(vertex=u)
                for s in pred:
                    if s != self.s_goal:
                        self.rhs[s] = min(self.rhs[s], self.c(s, u) + self.g[u])
                    self.update_vertex(s)
            else:
                self.g_old = self.g[u]
                self.g[u] = float('inf')
                pred = self.sensed_map.succ(vertex=u)
                pred.append(u)
                for s in pred:
                    if self.rhs[s] == self.c(s, u) + self.g_old:
                        if s != self.s_goal:
                            min_s = float('inf')
                            succ = self.sensed_map.succ(vertex=s)
                            for s_ in succ:
                                temp = self.c(s, s_) + self.g[s_]
                                if min_s > temp:
                                    min_s = temp
                            self.rhs[s] = min_s
                    self.update_vertex(s)

    def rescan(self) -> Vertices:

        new_edges_and_old_costs = self.new_edges_and_old_costs
        self.new_edges_and_old_costs = None
        return new_edges_and_old_costs

    def move_and_replan(self, robot_position: (int, int)):
        """
        Called each time the robot moves to a new position.
        Applies any pending edge cost changes, recomputes the shortest path,
        and returns the lookahead path from the current position to the goal.
        """
        self.s_start = robot_position

        # Apply changed edge costs if any were detected by SLAM
        changed_edges_with_old_cost = self.rescan()
        if changed_edges_with_old_cost:
            self.k_m += heuristic(self.s_last, self.s_start)
            self.s_last = self.s_start

            vertices = changed_edges_with_old_cost.vertices
            for vertex in vertices:
                v = vertex.pos
                succ_v = vertex.edges_and_c_old
                for u, c_old in succ_v.items():
                    c_new = self.c(u, v)
                    if c_old > c_new:
                        if u != self.s_goal:
                            self.rhs[u] = min(self.rhs[u], c_new + self.g[v])
                    elif self.rhs[u] == c_old + self.g[v]:
                        if u != self.s_goal:
                            min_cost = float('inf')
                            for s_ in self.sensed_map.succ(vertex=u):
                                min_cost = min(min_cost, self.c(u, s_) + self.g[s_])
                            self.rhs[u] = min_cost
                        self.update_vertex(u)

        self.compute_shortest_path()

        # Build lookahead path by greedily following minimum cost successors
        path = [self.s_start]
        s = self.s_start
        visited = {s}

        while s != self.s_goal:
            if self.rhs[s] == float('inf'):
                print(f"Warning: No path from {s} to {self.s_goal}")
                break

            succ = self.sensed_map.succ(s, avoid_obstacles=False)
            min_cost = float('inf')
            arg_min = None
            for s_ in succ:
                cost = self.c(s, s_) + self.g[s_]
                if cost < min_cost:
                    min_cost = cost
                    arg_min = s_

            if arg_min is None or arg_min in visited:
                break

            visited.add(arg_min)
            path.append(arg_min)
            s = arg_min

        return path, self.g, self.rhs