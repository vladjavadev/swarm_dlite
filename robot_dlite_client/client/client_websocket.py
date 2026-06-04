#!/usr/bin/env python
"""Client using the asyncio API."""
import asyncio
from websockets.asyncio.client import connect
import json
import utils.location_dto as ldt
import utils.dim_dto as ddt
import utils.connect_dto as con_dto




loc = ldt.LocationDTO()
dim_grid = ddt.DimDTO()
con = con_dto.Connection()
# uri = "ws://192.168.1.130:8765"
# uri = "ws://192.168.7.3:8765"
# uri = "ws://localhost:8765"
# uri = "ws://192.168.1.100:8765"
# uri = "ws://192.168.0.45:8765"
uri = "ws://localhost:8765"
m_types = ["set-obs","init-dim","init-points","set-weight"]


async def set_no_obs(grid_cell):
    d_nObs = {"no-obs": [grid_cell]}
    await send_message(m_types[0],d_nObs)

async def set_obs(grid_cell):
    d_Obs = {"obs": [grid_cell]}
    await send_message(m_types[0], d_Obs)

async def init_grid_message(grid_dim:tuple[int,int], unit:int):
    d_init = {"grid_dim":grid_dim, 
              "cell_unit":unit}
    
    await send_message(m_types[1], d_init)

async def init_points_message(start:tuple[int,int],goal:tuple[int,int] | None = None):
    if isinstance(start, list):
        d_init = {"drones": [{"start": point[0], "goal": point[1]} for point in start]}
    else:
        d_init = {"start":start,
                  "goal":goal}
    await send_message(m_types[2], d_init)

async def send_message(type, message):


    try:
        async with connect(uri) as websocket:
            event = {
                "type": type,
                **message
            }
            
            await websocket.send(json.dumps(event))
            print(f"✓ Событие отправлено: {event}")
            
            # Опционально: ожидание ответа от сервера
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Ответ сервера: {response}")
            except asyncio.TimeoutError:
                print("Сервер не ответил в течение 5 секунд")
            
    except ConnectionRefusedError:
        print("❌ Не удалось подключиться к серверу. Проверьте, что сервер запущен на ws://localhost:8765")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def send_obs_coord(grid_cell):
    asyncio.run(set_obs(grid_cell))


def send_points(start,goal=None):
    if goal is None and isinstance(start, list):
        asyncio.run(init_points_message(start))
    else:
        asyncio.run(init_points_message(start,goal))

def send_dim_grid(dim_grid, cell_unit):
    asyncio.run(init_grid_message(dim_grid, cell_unit))


def send_no_obs_coord(grid_cell):
    asyncio.run(set_no_obs(grid_cell))

async def send_set_weight(grid_cell, weight):
    d_weight = {"weight": [grid_cell, weight]}
    await send_message(m_types[3], d_weight)

def send_weight_coord(grid_cell, weight):
    asyncio.run(send_set_weight(grid_cell, weight))

def get_pos(location):
    asyncio.run(fetch_location(location))

def get_connection(con_dto):
    asyncio.run(fetch_connection_status(con_dto))

async def fetch_location(location):

    try:
        async with connect(uri) as websocket:
            event = {
                "type": "get-location"
            }
            
            await websocket.send(json.dumps(event))
            print(f"✓ Событие отправлено: {event}")
            
            # Опционально: ожидание ответа от сервера
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=40.0)
                event_pos = json.loads(response)
                if event_pos["type"] == "location":
                    if "current_pos" in event_pos:
                        goal = tuple(event_pos["goal"])
                        pos = tuple(event_pos["current_pos"])
                        path = event_pos["path"]
                        distance = event_pos["distance"]
                        pred_time = event_pos["pred_time"]
                        pred_distance = event_pos["pred_distance"]
                        drone_id = event_pos.get("drone_id", "drone_0")
                        loc.update(pos, path, goal, distance, pred_time, pred_distance, drone_id)
                        loc.collision_points = event_pos.get("collision_points", [])
                    elif "drones" in event_pos:
                        loc.update_all(event_pos["drones"], collision_points=event_pos.get("collision_points", []))

                print(f"Ответ сервера: {response}")
            except asyncio.TimeoutError:
                print("Сервер не ответил в течение 5 секунд")
            
    except ConnectionRefusedError:
        print("❌ Не удалось подключиться к серверу. Проверьте, что сервер запущен на ws://localhost:8765")
    except Exception as e:
        print(f"❌ Ошибка: {e}")



async def fetch_connection_status(con_dto):

    try:
        async with connect(uri) as websocket:
            event = {
                "type": "get-status"
            }
            
            await websocket.send(json.dumps(event))
            print(f"✓ Событие отправлено: {event}")
            
            # Опционально: ожидание ответа от сервера
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=40.0)
                event = json.loads(response)
                if event["type"] == "get-status":
                    if "status" in event:
                        con.update(event["status"])
                print(f"Ответ сервера: {response}")
            except asyncio.TimeoutError:
                print("Сервер не ответил в течение 5 секунд")
            
    except ConnectionRefusedError:
        print("❌ Не удалось подключиться к серверу. Проверьте, что сервер запущен на ws://localhost:8765")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def listen_for_events(gui):
    try:
        async with connect(uri) as websocket:
            while True:
                response = await websocket.recv()
                event = json.loads(response)
                if event["type"] == "set-weight":
                    if "weight" in event:
                        pos = event["weight"][0]
                        weight = event["weight"][1]
                        gui.set_weight(pos, weight)
                # можно добавить другие события
    except Exception as e:
        print(f"❌ Ошибка в listen_for_events: {e}")

def start_listening(gui):
    asyncio.run(listen_for_events(gui))

if __name__ == "__main__":
    try:
        asyncio.run(send_message())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")