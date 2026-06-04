
from dstar.d_star_lite import DStarLite
from dstar.grid import OccupancyGridMap, SLAM
import data as srv
import robot.move_logic as lgc
import time
from data.grid_dto import GridDto 

OBSTACLE = 255
UNOCCUPIED = 0


def run_algorithm(dto: GridDto, drone_id: str):

    """
    set initial values for the map occupancy grid and keep replanning for one drone
    """
    while dto.x_dim is None or dto.y_dim is None:
        print(f"[{drone_id}] Waiting for grid dimensions...")
        time.sleep(0.2)

    dto.build_world()
    start_pos = tuple(dto.get_position(drone_id))
    dto.set_position(start_pos, drone_id)
    goal = tuple(dto.get_goal(drone_id))
    view_range = 5

    new_map = dto.world
    old_map = new_map

    new_position = start_pos
    last_position = start_pos

    dstar = DStarLite(map=new_map,
                      s_start=start_pos,
                      s_goal=goal)

    slam = SLAM(map=new_map,
                view_range=view_range)

    def rebuild_dstar(start_position):
        nonlocal dstar
        dstar = DStarLite(map=new_map,
                          s_start=start_position,
                          s_goal=goal)
        return dstar

    path, g, rhs = dstar.move_and_replan(robot_position=new_position)
    if path is None:
        print(f"[{drone_id}] No valid path found from start to goal!")
        return

    print(f"[{drone_id}] Initial path found: {path}")

    if path:
        dto.set_path(path, drone_id)
        while True:
            try:
                time.sleep(0.1)
                start = time.time()

                new_position = dto.get_position(drone_id)
                new_observation = dto.observation
                new_map = dto.world

                if new_observation is not None and new_observation["type"] is not None:
                    old_map = new_map
                    slam.set_ground_truth_map(gt_map=new_map)

                if new_position != last_position:
                    dto._lock.acquire()
                    last_position = new_position

                    new_edges_and_old_costs, slam_map = slam.rescan(global_position=new_position)

                    dstar.new_edges_and_old_costs = new_edges_and_old_costs
                    dstar.sensed_map = slam_map

                    path, g, rhs = dstar.move_and_replan(robot_position=new_position)

                    dto.set_time_build_path(time.time()-start)
                    dto._lock.release()
                elif dto.is_map_changed():
                    dto.reset_map_changed()

                    dto._lock.acquire()
                    try:
                        recalc_start = time.time()

                        if new_observation is not None and new_observation.get("type") in {"WEIGHT", "COLLISION_OBSTACLE"}:
                            rebuild_dstar(start_position=new_position)
                            dstar.sensed_map = slam.slam_map
                        else:
                            dstar.new_edges_and_old_costs = None
                            dstar.sensed_map = slam.slam_map

                        path, g, rhs = dstar.move_and_replan(robot_position=new_position)
                        recalc_time = time.time() - recalc_start
                        if recalc_time > 1.0:
                            print(f"[{drone_id}] Warning: Path recalculation took {recalc_time:.2f}s (long)")

                        dto.set_time_build_path(time.time()-start)
                        print(f"[{drone_id}] Path recalculated due to map change at position {new_position} (time: {recalc_time:.3f}s)")
                    except Exception as e:
                        print(f"[{drone_id}] Error recalculating path: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        dto._lock.release()

                dto.set_path(path, drone_id)

            except TypeError as e:
                print(f"[{drone_id}] {e}")


if __name__ == "__main__":
    run_algorithm(srv.g_dt, "default")

