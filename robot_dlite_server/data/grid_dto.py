from dstar.grid import OccupancyGridMap 
from threading import Lock
import time

class DroneState:
    def __init__(self, start, goal):
        self.start = tuple(start)
        self.current = tuple(start)
        self.goal = tuple(goal)
        self.path = None
        self.totalDistance = 0
        self.pred_time = 0
        self.pred_distance = 0
        self._lock = Lock()
        self._lock_dist = Lock()


class GridDto:
    def __init__(self,
                 viewing_range=3):
        self.cell_unit = 200  # mm
        self.x_dim = None
        self.y_dim = None
        self.drones = {}
        self.observation = {"pos": None, "type": None}
        self.viewing_range = viewing_range
        self._lock = Lock()
        self.world = None
        self.time_build_path = 0.0
        self.map_changed = False

    def _resolve_drone_id(self, drone_id=None):
        if drone_id is not None:
            return drone_id
        if len(self.drones) == 1:
            return next(iter(self.drones))
        raise KeyError("drone_id is required when multiple drones are configured")

    def add_drone(self, drone_id: str, start, goal):
        if drone_id in self.drones:
            raise KeyError(f"Drone '{drone_id}' already exists")
        self.drones[drone_id] = DroneState(start, goal)

    def get_drone_state(self, drone_id: str = None):
        return self.drones[self._resolve_drone_id(drone_id)]

    def set_time_build_path(self, val):
        self.time_build_path = val

    def get_time_build_path(self):
        return self.time_build_path

    def set_predict_time_distance(self, time_val, distance, drone_id=None):
        state = self.get_drone_state(drone_id)
        state.pred_time = time_val
        state.pred_distance = distance

    def get_predict_time_distance(self, drone_id=None):
        state = self.get_drone_state(drone_id)
        return (state.pred_time, state.pred_distance)

    def build_world(self):
        self.world = OccupancyGridMap(x_dim=self.x_dim,
                                      y_dim=self.y_dim,
                                      exploration_setting='8N')

    def set_distance(self, dist, drone_id=None):
        state = self.get_drone_state(drone_id)
        with state._lock_dist:
            state.totalDistance = dist

    def get_total_distance(self, drone_id=None):
        state = self.get_drone_state(drone_id)
        return state.totalDistance

    def set_unit(self, cell_unit):
        self.cell_unit = cell_unit

    def get_unit(self):
        return self.cell_unit

    def set_dim(self, dim_tuple):
        self.x_dim = dim_tuple[0]
        self.y_dim = dim_tuple[1]
        self.build_world()

    def set_path(self, path=None, drone_id=None):
        state = self.get_drone_state(drone_id)
        with state._lock:
            state.path = path

    def get_path(self, drone_id=None):
        state = self.get_drone_state(drone_id)
        with state._lock:
            return state.path

    def get_time(self):
        return self._time_build_path

    def get_position(self, drone_id=None):
        state = self.get_drone_state(drone_id)
        with state._lock:
            return state.current

    def set_position(self, pos: (int, int), drone_id=None):
        state = self.get_drone_state(drone_id)
        with state._lock:
            state.current = tuple(pos)

    def get_goal(self, drone_id=None):
        state = self.get_drone_state(drone_id)
        return state.goal

    def set_goal(self, goal: (int, int), drone_id=None):
        state = self.get_drone_state(drone_id)
        state.goal = tuple(goal)

    def set_start(self, start: (int, int), drone_id=None):
        state = self.get_drone_state(drone_id)
        state.start = tuple(start)
        state.current = tuple(start)

    def set_obs(self, grid_cell: (int, int)):
        with self._lock:
            if self.world.is_unoccupied(grid_cell):
                self.world.set_obstacle(grid_cell)
                self.observation = {"pos": grid_cell, "type": "OBSTACLE"}
                self.map_changed = True

    def rem_obs(self, grid_cell: (int, int)):
        with self._lock:
            if not self.world.is_unoccupied(grid_cell):
                print("grid cell: ".format(grid_cell))
                self.world.remove_obstacle(grid_cell)
                self.observation = {"pos": grid_cell, "type": "UNOCCUPIED"}
                self.map_changed = True

    def set_weight(self, grid_cell: (int, int), weight: float):
        with self._lock:
            self.world.set_weight(grid_cell, weight)
            self.observation = {"pos": grid_cell, "type": "WEIGHT", "weight": weight}
            self.map_changed = True

    def is_map_changed(self) -> bool:
        with self._lock:
            return self.map_changed

    def reset_map_changed(self):
        with self._lock:
            self.map_changed = False

    def get_weight(self, grid_cell: (int, int)) -> float:
        with self._lock:
            return self.world.get_weight(grid_cell)