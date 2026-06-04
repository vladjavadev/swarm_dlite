#!/usr/bin/env python

"""Echo server using the asyncio API."""

import asyncio
from websockets.asyncio.server import serve, ServerConnection
from data.grid_dto import GridDto
from robot.move_logic import Logic
import core.algorithm as agm
from path_observation import PathObservation
import json
import threading
import time
import functools
from typing import Dict, List, Set, Tuple

# change value for 2 mode
mode = 3
g_dt = GridDto()
logics = {}
# ip="0.0.0.0"
ip = "localhost"

async def echo(dto:GridDto, websocket:ServerConnection):
    try:
        async for message in websocket:
            event = json.loads(message)
           
            # assert event["type"] == "start"
            if event["type"] == "set-obs":
                
                if "obs" in event:
                    # print("<!------",event["obs"][0],"------!>")
                    dto.set_obs(event["obs"][0])
                    await websocket.send(json.dumps({"type": "ack", "status": "obstacle_set"}))
                elif "no-obs" in event:
                    dto.rem_obs(event["no-obs"][0])
                    await websocket.send(json.dumps({"type": "ack", "status": "obstacle_removed"}))
                    
            elif event["type"] == "set-weight":
                if "weight" in event:
                    pos = event["weight"][0]
                    weight = event["weight"][1]
                    dto.set_weight(pos, weight)
                    await websocket.send(json.dumps({"type": "ack", "status": "weight_set", "pos": pos, "weight": weight}))
                    
            elif event["type"] == "get-location":
                if "drone_id" in event:
                    drone_id = event["drone_id"]
                    pos = dto.get_position(drone_id)
                    goal = dto.get_goal(drone_id)
                    path = dto.get_path(drone_id)
                    totalDistance = dto.get_total_distance(drone_id)
                    pred_time, pred_distance = dto.get_predict_time_distance(drone_id)
                    event_location = {
                        "type": "location",
                        "drone_id": drone_id,
                        "current_pos": pos,
                        "goal": goal,
                        "path": path,
                        "distance": totalDistance,
                        "pred_time": pred_time,
                        "pred_distance": pred_distance,
                        "collision_points": dto.get_collision_points()
                    }
                else:
                    drones = []
                    for drone_id in dto.drones.keys():
                        drones.append({
                            "drone_id": drone_id,
                            "current_pos": dto.get_position(drone_id),
                            "goal": dto.get_goal(drone_id),
                            "path": dto.get_path(drone_id),
                            "distance": dto.get_total_distance(drone_id),
                            "pred_time": dto.get_predict_time_distance(drone_id)[0],
                            "pred_distance": dto.get_predict_time_distance(drone_id)[1]
                        })
                    event_location = {
                        "type": "location",
                        "drones": drones,
                        "collision_points": dto.get_collision_points()
                    }
                await websocket.send(json.dumps(event_location))

            elif event["type"] == "get-status":
                event_connected = {
                    "type":"get-status",
                    "status":"connected"
                }
                await websocket.send(json.dumps(event_connected))
                
            elif event["type"] == "init-dim":
                dto.set_dim(event["grid_dim"])
                dto.set_unit(event["cell_unit"])
                await websocket.send(json.dumps({"type": "ack", "status": "dimensions_set"}))

            elif event["type"] == "init-points":
                drone_configs = []
                if "drones" in event and isinstance(event["drones"], list):
                    drone_configs = event["drones"]
                elif "points" in event and isinstance(event["points"], list):
                    drone_configs = event["points"]
                else:
                    drone_configs = [{
                        "id": event.get("id", "drone_0"),
                        "start": event["start"],
                        "goal": event["goal"],
                        "mode": event.get("mode", mode)
                    }]

                started_drones = []
                for drone_data in drone_configs:
                    drone_id = drone_data.get("id") or f"drone_{len(logics)}"
                    start = drone_data["start"]
                    goal = drone_data["goal"]
                    drone_mode = drone_data.get("mode", mode)

                    dto.add_drone(drone_id, start, goal)
                    logic = Logic(drone_id=drone_id, vMode=drone_mode)
                    logic.init_dto(dto)
                    logics[drone_id] = logic

                    algo_thread = DoWork(task_func=agm.run_algorithm, args=(dto, drone_id), name=f"algo-{drone_id}")
                    move_thread = DoWork(task_func=moving_robot, args=(logic,), name=f"move-{drone_id}")
                    algo_thread.start()
                    move_thread.start()
                    started_drones.append(drone_id)

                await websocket.send(json.dumps({"type": "ack", "status": "path_planning_started", "drones": started_drones}))
            else:
                await websocket.send(json.dumps({"type": "error", "message": "Unknown command"}))
    except Exception as e:
        print(f"Error in echo handler: {e}")


def build_trajectory(path: List[Tuple[int, int]], current_pos: Tuple[int, int] = None) -> List[Tuple[int, int]]:
    if not path:
        return [current_pos] if current_pos is not None else []
    trajectory = list(path)
    if current_pos is not None and trajectory and trajectory[0] != current_pos:
        trajectory.insert(0, current_pos)
    return trajectory


def detect_predicted_collision_points(dto: GridDto) -> Set[Tuple[int, int]]:
    paths = {}
    for drone_id in dto.drones:
        path = dto.get_path(drone_id)
        if path is None:
            continue
        paths[drone_id] = build_trajectory(path, dto.get_position(drone_id))

    collisions = set()
    drone_ids = list(paths.keys())
    for i in range(len(drone_ids)):
        for j in range(i + 1, len(drone_ids)):
            path_a = paths[drone_ids[i]]
            path_b = paths[drone_ids[j]]
            if not path_a or not path_b:
                continue
            max_steps = max(len(path_a), len(path_b))
            for t in range(max_steps):
                pos_a = path_a[t] if t < len(path_a) else path_a[-1]
                pos_b = path_b[t] if t < len(path_b) else path_b[-1]
                if pos_a == pos_b:
                    collisions.add(pos_a)
                if t > 0:
                    prev_a = path_a[t - 1] if t - 1 < len(path_a) else path_a[-1]
                    prev_b = path_b[t - 1] if t - 1 < len(path_b) else path_b[-1]
                    if pos_a == prev_b and pos_b == prev_a:
                        collisions.add(pos_a)
                        collisions.add(pos_b)
    return collisions


def update_predicted_collisions(dto: GridDto) -> Set[Tuple[int, int]]:
    dto.clear_collision_obstacles()
    collision_points = detect_predicted_collision_points(dto)
    for point in collision_points:
        dto.mark_collision_point(point)
    return collision_points


def build_collision_group_map(dto: GridDto, collision_points: Set[Tuple[int, int]]) -> Dict[Tuple[int, int], List[Tuple[str, int]]]:
    group_map = {}
    for drone_id, path in dto.get_all_paths().items():
        if path is None:
            continue
        trajectory = build_trajectory(path, dto.get_position(drone_id))
        for step, pos in enumerate(trajectory):
            if pos not in collision_points:
                continue
            group_map.setdefault(pos, []).append((drone_id, step))

    for pos in list(group_map.keys()):
        group_map[pos].sort(key=lambda item: (item[1], item[0]))
    return group_map


def should_yield_for_collision(dto: GridDto, drone_id: str, collision_point: Tuple[int, int]) -> bool:
    collision_points = detect_predicted_collision_points(dto)
    group_map = build_collision_group_map(dto, collision_points)
    group = group_map.get(collision_point)
    if not group or len(group) < 2:
        return False

    best_step = group[0][1]
    best_drone_ids = [did for did, step in group if step == best_step]
    if len(best_drone_ids) > 1:
        allowed_drone = max(best_drone_ids)
    else:
        allowed_drone = best_drone_ids[0]

    return drone_id != allowed_drone


async def get_pos(dto: GridDto, websocket:ServerConnection):
    pos = dto.get_position()
    websocket.send(pos)

        

async def main():
    print("<!!!! Run SERVER !!!!>")
    bound_handler = functools.partial(echo, g_dt)
    async with serve(bound_handler, ip, 8765) as server:
        await server.serve_forever()


def moving_robot(logic: Logic):
    time.sleep(5.0)
    last_path = []
    next_pos = None
    last_pred_time = 0
    _lock = threading.Lock()

    trajectory_times = []
    pred_times = []
    path_build_time_list = []

    p_obs = PathObservation()
    threading.Thread(target=move_process, args=(p_obs, logic, trajectory_times)).start()
    start_time = time.time()
    while True:
        try:
            time.sleep(0.1)
            path = logic.dto.get_path(logic.drone_id)
            if path is not None:
                update_predicted_collisions(logic.dto)
                if path != last_path:
                    if len(path) > 1:
                        if not p_obs.is_updated:
                            _lock.acquire()
                            next_pos = path[1]
                            if next_pos in logic.dto.get_collision_points() and should_yield_for_collision(logic.dto, logic.drone_id, next_pos):
                                print(f"[{logic.drone_id}] Yielding at {next_pos} for another drone to pass")
                                logic.stop()
                                _lock.release()
                                continue
                            p_obs.update(next_pos)
                            ptime, pdistance = logic.predict_time_distance(path)
                            if last_pred_time != ptime or len(pred_times) == 0:
                                pred_times.append(ptime)
                                path_build_time = logic.dto.get_time_build_path()
                                path_build_time_list.append(path_build_time)
                            logic.dto.set_predict_time_distance(ptime, pdistance, logic.drone_id)
                            last_pred_time = pred_times[-1]
                            last_path = path
                            _lock.release()
                elif len(path) > 1 and path[1] in logic.dto.get_collision_points():
                    if should_yield_for_collision(logic.dto, logic.drone_id, path[1]):
                        print(f"[{logic.drone_id}] Yielding at {path[1]} for another drone to pass")
                        logic.stop()
                        continue
                    print(f"[{logic.drone_id}] Passing through collision point {path[1]}")
                    continue

            if logic.dto.get_position(logic.drone_id) == tuple(logic.dto.get_goal(logic.drone_id)):
                print(f"MOVE ROBOT POS:{logic.dto.get_position(logic.drone_id)}")
                p_obs.is_done = True
                print(f"Client: Reached Goal for {logic.drone_id}!")
                jsonData = {
                    "build_trajectory_times": trajectory_times,
                    "predict_times": pred_times,
                    "path_build_times": path_build_time_list
                }
                print("Total time: ", time.time() - start_time)
                print(json.dumps(jsonData, indent=4))
                break
        except Exception as e:
            print("MOVING ROBOT EXCEPTION:", e)
            p_obs.is_done = True
            logic.stop()


class DoWork(threading.Thread):
    def __init__(self, task_func, shared=None, args=(), kwargs=None, *thread_args, **thread_kwargs):
        super(DoWork, self).__init__(*thread_args, **thread_kwargs)
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs or {}
        self.shared = shared

    def run(self):
        print(threading.current_thread(), 'start')
        time.sleep(1)
        if self.shared is not None and not self.args:
            self.task_func(self.shared, **self.kwargs)
        else:
            self.task_func(*self.args, **self.kwargs)
        print(threading.current_thread(), 'done')


def move_process(p_obs: PathObservation, logic: Logic, route_times: List[int]):
    counter = 0
    update_time_start = time.time()
    while True:
        time.sleep(0.02)
        if p_obs.is_updated:
            build_route_time = logic.build_route(p_obs.next_pos)
            logic.dto.set_position(p_obs.next_pos, logic.drone_id)
            if build_route_time:
                route_times.append(build_route_time)
            p_obs.is_updated = False
            counter = 0
        elif counter == 5:
            print("No path update, stop robot ", time.time() - update_time_start)
            update_time_start = time.time()
            logic.stop()
        elif p_obs.is_done:
            route_times.append(0)
            logic.stop()
            break

        counter = counter % 5 + 1


def run_server(dto):
    asyncio.run(main())


if __name__ == "__main__":
 
    threads = [ DoWork(shared=g_dt, task_func=run_server, name='c')]
    for t in threads:
        t.start()

    for t in threads:
        t.join()
   

