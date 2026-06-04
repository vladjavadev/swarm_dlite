import pygame
import time
from typing import List, Tuple
import numpy as np
from client import client_websocket as cw
import threading
import math


# Define some colors
BLACK = (0, 0, 0)  # BLACK
UNOCCUPIED = (255, 255, 255)  # WHITE
GOAL = (0, 255, 0)  # GREEN
START = (255, 0, 0)  # RED
COLLISION_POINT = (255, 165, 0)  # ORANGE
GRAY1 = (145, 145, 102)  # GRAY1
OBSTACLE = (77, 77, 51)  # GRAY2
LOCAL_GRID = (0, 0, 80)  # BLUE



colors = {
    0: UNOCCUPIED,
    1: GOAL,
    255: OBSTACLE
}

weight_colors = {
    1: (94, 247, 143),    # нормальная поверхность
    2: (20, 243, 255),    # слегка затрудненная
    4: (150, 150, 150),    # средняя
    6: (24, 81, 196),   # трудная
    10: (50, 50, 50),     # очень трудная
}

DRONE_COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 165, 0),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 0),
    (128, 0, 128),
    (0, 128, 128),
]

def check_loop(gui):
    time.sleep(1.0)
    obs_attr = [
                (200,200,0,35),(200,200,60,35),
                (200,150,0,50),(150,100,0,45),
                (200,200,10,75),(200,200,10,80),
                (200,200,60,80), (350,800,35,40)
                ]
    # gui.init_obstacles(obs_attr,gui.cell_size)

    while not gui.done:
        cw.get_pos(cw.loc)
        time.sleep(1.0)


class Animation:
    def __init__(self,
                 title="D* Lite Path Planning",
                 width=20,
                 height=20,
                 margin=2,
                 x_dim=10,
                 y_dim=10,
                 start=(1, 1),
                 goal=(8, 8),
                 cell_size=200,
                 viewing_range=1):
        pygame.init()
        self.width = width
        self.height = height
        self.margin = margin
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.start = start
        self.current = start
        self.observation = {"pos": None, "type": None}
        self.goal = goal
        self.viewing_range = viewing_range
        self.traject = []
        self.drone_traces = {}
        self.drone_colors = {}
        self.totalDistance=0
        self.pred_time=0
        self.pred_distance=0
        self.cell_size=cell_size
        pygame.font.SysFont('Comic Sans MS', 36)
        self.font = pygame.font.Font(None, 16)
        self.btmFrame = 150



        pygame.init()

        # Set the 'width' and 'height' of the screen
        window_size = [(width + margin) * y_dim + margin,
                       self.btmFrame+(height + margin) * x_dim + margin]

        self.screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)

        # create occupancy grid map
        """
        set initial values for the map occupancy grid
        |----------> y, column
        |           (x=0,y=2)
        |
        V (x=2, y=0)
        x, row
        """

        self.map_extents = (x_dim, y_dim)

        # the obstacle map
        self.occupancy_grid_map = np.zeros(self.map_extents, dtype=np.uint8)

        # the weight map
        self.weight_grid = np.ones(self.map_extents, dtype=np.float32)

        self.world = self.map_extents

        # Set title of screen
        pygame.display.set_caption(title)

        # set font
        pygame.font.SysFont('Comic Sans MS', 18)

        # Loop until the user clicks the close button
        self.done = False

        # used to manage how fast the screen updates
        self.clock = pygame.time.Clock()

    def get_position(self):
        return self.current

    def set_position(self, pos: tuple[int, int]):
        self.current = pos

    def get_goal(self):
        return self.goal

    def set_goal(self, goal: tuple[int, int]):
        self.goal = goal

    def set_start(self, start: tuple[int, int]):
        self.start = start

    def set_weight(self, pos, weight):
        if 0 <= pos[0] < self.x_dim and 0 <= pos[1] < self.y_dim:
            self.weight_grid[pos[0], pos[1]] = weight

    def display_path(self, path=None,color=START):
        if path is not None:
            for step in path:
                # draw a moving robot, based on current coordinates
                step_center = [round(step[1] * (self.width + self.margin) + self.width / 2) + self.margin,
                               round(step[0] * (self.height + self.margin) + self.height / 2) + self.margin]

                # draw robot position as red circle
                pygame.draw.circle(self.screen, color, step_center, round(self.width / 2) - 2)

    def get_drone_color(self, drone_id):
        if drone_id not in self.drone_colors:
            index = len(self.drone_colors) % len(DRONE_COLORS)
            self.drone_colors[drone_id] = DRONE_COLORS[index]
        return self.drone_colors[drone_id]

    def _scale_obstacles(self, obs: List[Tuple[int,int,int,int]], cell_size: int):
        scaled = []
        for (x_mm, y_mm,x_s,y_s) in obs:
            x = round(x_s/100*self.x_dim)
            y = round(y_s/100*self.y_dim)
            cell_x = math.ceil(x_mm / cell_size)
            cell_y = math.ceil(y_mm / cell_size)
            for i in range(0,cell_x):
                for j in range(0,cell_y):
                    obs_x = x + i
                    obs_y = y + j
                    if 0 <= obs_x < self.x_dim and 0 <= obs_y< self.y_dim:
                        scaled.append((x+i, y+j))
        return scaled

    def init_obstacles(self, obs_attr:List[Tuple[int,int,int,int]], cell_size:int):
        """
        obs_attr : obstacles attributes size and position in percent as list of tuples (x_mm,y_mm,x,y)
        cell_size    : size of one cell in mm
        """

        obs = self._scale_obstacles(obs_attr, cell_size)
        for o in obs:
            self.occupancy_grid_map[o[0], o[1]] = 255
            cw.send_obs_coord(o)
            cw.send_weight_coord(o, 1000)  # задаем высокий вес для преград

    def display_obs(self, observations=None):
        if observations is not None:
            for o in observations:
                pygame.draw.rect(self.screen, GRAY1, [(self.margin + self.width) * o[1] + self.margin,
                                                      (self.margin + self.height) * o[0] + self.margin,
                                                      self.width,
                                                      self.height])

    def display_collision_points(self, points=None):
        if points is not None:
            for point in points:
                pygame.draw.rect(self.screen, COLLISION_POINT,
                                 [(self.margin + self.width) * point[1] + self.margin,
                                  (self.margin + self.height) * point[0] + self.margin,
                                  self.width,
                                  self.height])

    def draw_legend(self):
        legend_items = [
            (10, weight_colors[10], "Очень трудная"),
            (6, weight_colors[6], "Трудная"),
            (4, weight_colors[4], "Средняя"),
            (2, weight_colors[2], "Слегка затрудненная"),
            (1, weight_colors[1], "Нормальная"),
            (0, COLLISION_POINT, "Collision point"),
        ]
        legend_width = 220
        legend_height = 24 + len(legend_items) * 22
        x = self.screen.get_width() - legend_width - 10
        y = 10
        pygame.draw.rect(self.screen, (20, 20, 20), (x, y, legend_width, legend_height))
        pygame.draw.rect(self.screen, (200, 200, 200), (x, y, legend_width, legend_height), 1)
        title = self.font.render("Легенда цветов", True, (255, 255, 255))
        self.screen.blit(title, (x + 10, y + 3))
        for idx, (weight, color, label) in enumerate(legend_items):
            row_y = y + 24 + idx * 22
            pygame.draw.rect(self.screen, color, (x + 10, row_y, 20, 20))
            text = self.font.render(f"{label} (w={weight})", True, (255, 255, 255))
            self.screen.blit(text, (x + 36, row_y))

    def run_game(self):
        thread = threading.Thread(target=check_loop, daemon=True,args=(self,))
        thread.start()
        listen_thread = threading.Thread(target=cw.start_listening, daemon=True, args=(self,))
        listen_thread.start()
        path = cw.loc.get_path()
        flag = True
        while not self.done:
            if path is None:
                path = []

            grid_cell = None
            self.cont = False
            for event in pygame.event.get():

                if event.type == pygame.QUIT:  # if user clicked close
                    print("quit")
                    self.done = True  # flag that we are done so we can exit loop
                    raise KeyboardInterrupt("GUI closed by user")
                elif (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or self.cont:
                    # space bar pressed. call next action
                    if path:
                        (x, y) = path[1]
                        self.set_position((x, y))

                elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                    print("backspace automates the press space")
                    if not self.cont:
                        self.cont = True
                    else:
                        self.cont = False

                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                    (col, row) = pygame.mouse.get_pos()
                    x = row // (self.height + self.margin)
                    y = col // (self.width + self.margin)
                    if 0 <= x < self.x_dim and 0 <= y < self.y_dim:
                        grid_cell = (x, y)
                        weight_map = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 5, pygame.K_4: 10, pygame.K_5: 100}
                        weight = weight_map[event.key]
                        self.set_weight(grid_cell, weight)
                        cw.send_weight_coord(grid_cell, weight)
                        if self.occupancy_grid_map[grid_cell[0], grid_cell[1]] == 255:
                            self.occupancy_grid_map[grid_cell[0], grid_cell[1]] = 0
                            cw.send_no_obs_coord(grid_cell)

                # set obstacle by holding left-click
                elif pygame.mouse.get_pressed()[0]:
                    # User clicks the mouse. Get the position
                    (col, row) = pygame.mouse.get_pos()

                    # change the x/y screen coordinates to grid coordinates
                    x = row // (self.height + self.margin)
                    y = col // (self.width + self.margin)

                    if 0 <= x < self.x_dim and 0 <= y < self.y_dim:
                        # turn pos into cell
                        grid_cell = (x, y)

                        # set the location in the grid map
                        # if self.world.is_unoccupied(grid_cell):
                        #     self.world.set_obstacle(grid_cell)
                        #     self.observation = {"pos": grid_cell, "type": OBSTACLE}
                        cw.send_obs_coord(grid_cell)
                        cw.send_weight_coord(grid_cell, 1000)
                        self.occupancy_grid_map[grid_cell[0], grid_cell[1]] = 255

                # remove obstacle by holding right-click
                elif pygame.mouse.get_pressed()[2]:
                    # User clicks the mouse. Get the position
                    (col, row) = pygame.mouse.get_pos()

                    # change the x/y screen coordinates to grid coordinates
                    x = row // (self.height + self.margin)
                    y = col // (self.width + self.margin)

                    if 0 <= x < self.x_dim and 0 <= y < self.y_dim:
                        # turn pos into cell
                        grid_cell = (x, y)

                        # set the location in the grid map
                        # if not self.world.is_unoccupied(grid_cell):
                        #     print("grid cell: ".format(grid_cell))
                        #     self.world.remove_obstacle(grid_cell)
                        #     self.observation = {"pos": grid_cell, "type": UNOCCUPIED}

                        cw.send_no_obs_coord(grid_cell)
                        cw.send_weight_coord(grid_cell, 1)
                        self.occupancy_grid_map[grid_cell[0], grid_cell[1]] = 0

            # set the screen background
            self.screen.fill(BLACK)

            # draw the grid
            for row in range(self.x_dim):
                for column in range(self.y_dim):
                    # color the cells
                    if self.occupancy_grid_map[row][column] == 255:
                        color = OBSTACLE
                    else:
                        weight = self.weight_grid[row, column]
                        color = weight_colors.get(weight, UNOCCUPIED)
                    pygame.draw.rect(self.screen, color,
                                    [(self.margin + self.width) * column + self.margin,
                                    (self.margin + self.height) * row + self.margin,
                                    self.width,
                                    self.height])

            drones = cw.loc.get_all_drones() or {}
            first_drone = next(iter(drones.values()), None)
            if first_drone is not None:
                self.current = first_drone["current_pos"]
                self.goal = first_drone["goal"]
                self.totalDistance = first_drone["totalDistance"]
                self.pred_distance = first_drone["pred_distance"]
                self.pred_time = first_drone["pred_time"]
            else:
                self.current = cw.loc.get_pos()
                self.goal = cw.loc.get_goal()
                self.totalDistance = cw.loc.get_total_distance()
                self.pred_distance = cw.loc.get_pred_distance()
                self.pred_time = cw.loc.get_pred_time()

            collision_points = cw.loc.get_collision_points()
            if collision_points:
                self.display_collision_points(collision_points)

            for drone_id, drone_data in drones.items():
                color = self.get_drone_color(drone_id)
                current = tuple(drone_data.get("current_pos", self.current))
                path = drone_data.get("path") or []
                goal = tuple(drone_data.get("goal", self.goal))

                self.drone_traces.setdefault(drone_id, []).append(current)
                self.display_path(path=self.drone_traces[drone_id], color=color)
                self.display_path(path=path, color=color)

                goal_rect = [(self.margin + self.width) * goal[1] + self.margin,
                             (self.margin + self.height) * goal[0] + self.margin,
                             self.width,
                             self.height]
                pygame.draw.rect(self.screen, color, goal_rect, 3)

                robot_center = [round(current[1] * (self.width + self.margin) + self.width / 2) + self.margin,
                                round(current[0] * (self.height + self.margin) + self.height / 2) + self.margin]
                pygame.draw.circle(self.screen, color, robot_center, round(self.width / 2) - 2)
                
                # draw scanning area frame for each drone
                pygame.draw.rect(self.screen, color,
                                [robot_center[0] - self.viewing_range * (self.height + self.margin),
                                 robot_center[1] - self.viewing_range * (self.width + self.margin),
                                 2 * self.viewing_range * (self.height + self.margin),
                                 2 * self.viewing_range * (self.width + self.margin)], 1)

            if not drones:
                self.display_path(path=self.traject, color=(255,255,0))
                self.display_path(path=cw.loc.get_path())
                robot_center = [round(self.current[1] * (self.width + self.margin) + self.width / 2) + self.margin,
                                round(self.current[0] * (self.height + self.margin) + self.height / 2) + self.margin]
                pygame.draw.circle(self.screen, START, robot_center, round(self.width / 2) - 2)
                pygame.draw.rect(self.screen, GOAL, [(self.margin + self.width) * self.goal[1] + self.margin,
                                                    (self.margin + self.height) * self.goal[0] + self.margin,
                                                    self.width,
                                                    self.height])

            self.draw_legend()

            info_y = (self.height + self.margin) * self.x_dim + 10
            for idx, (drone_id, drone_data) in enumerate(drones.items()):
                color = self.get_drone_color(drone_id)
                text = self.font.render(
                    f"{drone_id}: pos={tuple(drone_data.get('current_pos', (0,0)))} goal={tuple(drone_data.get('goal', (0,0)))} dist={drone_data.get('totalDistance', 0):.0f}",
                    True,
                    color
                )
                self.screen.blit(text, (10, info_y + idx * 18))

            # draw robot local grid map (viewing range)
            if self.current is not None:
                robot_center = [round(self.current[1] * (self.width + self.margin) + self.width / 2) + self.margin,
                                round(self.current[0] * (self.height + self.margin) + self.height / 2) + self.margin]
                pygame.draw.rect(self.screen, LOCAL_GRID,
                                [robot_center[0] - self.viewing_range * (self.height + self.margin),
                                robot_center[1] - self.viewing_range * (self.width + self.margin),
                                2 * self.viewing_range * (self.height + self.margin),
                                2 * self.viewing_range * (self.width + self.margin)], 2)
            
            text_distance = self.font.render(f"Total Distance: {self.totalDistance:.0f} mm", True, (255, 0, 0))
            text_rect = text_distance.get_rect()
            text_rect.centerx = (self.width + self.margin) * self.y_dim // 2
            text_rect.top = (self.height + self.margin) * self.x_dim + 10
            self.screen.blit(text_distance, text_rect)

            text_pred_distance = self.font.render(f"Predicted Distance: {self.pred_distance:.0f} mm", True, (255, 0, 0))
            text_pred_rect = text_pred_distance.get_rect()
            text_pred_rect.centerx = (self.width + self.margin) * self.y_dim // 2
            text_pred_rect.top = (self.height + self.margin) * self.x_dim + 40
            self.screen.blit(text_pred_distance, text_pred_rect)

            text_pred_time = self.font.render(f"Predicted Time: {self.pred_time:.0f} seconds", True, (255, 0, 0))
            text_pred_time_rect = text_pred_time.get_rect()
            text_pred_time_rect.centerx = (self.width + self.margin) * self.y_dim // 2
            text_pred_time_rect.top = (self.height + self.margin) * self.x_dim + 70
            self.screen.blit(text_pred_time, text_pred_time_rect)

            # set game tick
            self.clock.tick(20)

            # go ahead and update screen with that we've drawn
            pygame.display.flip()

        # be 'idle' friendly. If you forget this, the program will hang on exit
        pygame.quit()


x_dim = 10
y_dim = 10
start = (1, 1)
goal = (8, 8)
view_range = 1


gui = Animation(title="D* Lite Path Planning",
                    width=50,
                    height=50,
                    margin=1,
                    x_dim=x_dim,
                    y_dim=y_dim,
                    start=start,
                    goal=goal,
                    viewing_range=view_range)


