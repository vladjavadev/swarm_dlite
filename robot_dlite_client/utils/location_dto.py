class LocationDTO:
    def __init__(self):
        self.drones = {}
        self._latest_drone_id = None
        self._latest_pos = (0, 0)
        self._latest_path = []
        self.goal = (0, 0)
        self.totalDistance = 0
        self.pred_time = 0
        self.pred_distance = 0
        self.collision_points = []
        self._timestamp = None

    def _resolve_drone_id(self, drone_id=None):
        if drone_id is not None:
            return drone_id
        if self._latest_drone_id is not None:
            return self._latest_drone_id
        if self.drones:
            return next(iter(self.drones))
        return None

    def update(self, new_pos, new_path, goal, distance, pred_time, pred_distance, drone_id="drone_0"):
        drone_id = drone_id or "drone_0"
        self.drones[drone_id] = {
            "current_pos": tuple(new_pos),
            "path": new_path,
            "goal": tuple(goal),
            "totalDistance": distance,
            "pred_time": pred_time,
            "pred_distance": pred_distance,
        }
        self._latest_drone_id = drone_id
        self._latest_pos = tuple(new_pos)
        self._latest_path = new_path
        self.goal = tuple(goal)
        self.totalDistance = distance
        self.pred_time = pred_time
        self.pred_distance = pred_distance
        self.collision_points = []

    def update_all(self, drones, collision_points=None):
        self.drones = {}
        for index, drone in enumerate(drones):
            drone_id = drone.get("drone_id") or f"drone_{index}"
            self.drones[drone_id] = {
                "current_pos": tuple(drone.get("current_pos", (0, 0))),
                "path": drone.get("path", []),
                "goal": tuple(drone.get("goal", (0, 0))),
                "totalDistance": drone.get("distance", 0),
                "pred_time": drone.get("pred_time", 0),
                "pred_distance": drone.get("pred_distance", 0),
            }
        self.collision_points = collision_points or []
        if self.drones:
            self._latest_drone_id = next(iter(self.drones))
            first = self.drones[self._latest_drone_id]
            self._latest_pos = first["current_pos"]
            self._latest_path = first["path"]
            self.goal = first["goal"]
            self.totalDistance = first["totalDistance"]
            self.pred_time = first["pred_time"]
            self.pred_distance = first["pred_distance"]

    def get_all_drones(self):
        return self.drones

    def get_pred_time(self, drone_id=None):
        drone_id = self._resolve_drone_id(drone_id)
        if drone_id and drone_id in self.drones:
            return self.drones[drone_id]["pred_time"]
        return self.pred_time
    
    def get_pred_distance(self, drone_id=None):
        drone_id = self._resolve_drone_id(drone_id)
        if drone_id and drone_id in self.drones:
            return self.drones[drone_id]["pred_distance"]
        return self.pred_distance
    
    def get_pos(self, drone_id=None):
        drone_id = self._resolve_drone_id(drone_id)
        if drone_id and drone_id in self.drones:
            return self.drones[drone_id]["current_pos"]
        return self._latest_pos

    def get_path(self, drone_id=None):
        drone_id = self._resolve_drone_id(drone_id)
        if drone_id and drone_id in self.drones:
            return self.drones[drone_id]["path"]
        return self._latest_path
    
    def get_goal(self, drone_id=None):
        drone_id = self._resolve_drone_id(drone_id)
        if drone_id and drone_id in self.drones:
            return self.drones[drone_id]["goal"]
        return self.goal
    
    def get_total_distance(self, drone_id=None):
        drone_id = self._resolve_drone_id(drone_id)
        if drone_id and drone_id in self.drones:
            return self.drones[drone_id]["totalDistance"]
        return self.totalDistance

    def get_collision_points(self):
        return getattr(self, "collision_points", [])

