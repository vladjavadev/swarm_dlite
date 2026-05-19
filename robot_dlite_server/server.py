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
from typing import List

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
                        "pred_distance": pred_distance
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
                    event_location = {"type": "location", "drones": drones}
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
            if path is not None and path != last_path:
                if len(path) > 1:
                    if not p_obs.is_updated:
                        _lock.acquire()
                        next_pos = path[1]
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
   

