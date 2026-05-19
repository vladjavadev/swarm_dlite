import pygame
import numpy as np
from client import client_websocket as cw
import time


class InputField:
    def __init__(self,pos_x,pos_y,width=60,height=40):
        self.x= pos_x
        self.y=pos_y
        self.field =  pygame.Rect(pos_x,pos_y,width,height)
        self.clr_lock = pygame.Color('lightskyblue3')
        self.clr_edit = pygame.Color('dodgerblue2')
        self.color = self.clr_lock
        self.active = False
        self.text=''

class GridGUI:
    def __init__(self, title="Init Dim GRID",
                 width=20, height=20, margin=2,
                 x_dim=10, y_dim=10):
        self.width = width
        self.height = height
        self.margin = margin
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.pending_start = None
        self.drone_pairs = []

        self.gui_grid = np.ones((x_dim, y_dim, 3), dtype=np.uint8) * 255

        pygame.init()
        window_size = [(width + margin) * y_dim + margin,
                    (height + margin) * x_dim + margin+60]
        
        # после вычисления window_size
        win_w, win_h = window_size

        # кнопка OK внизу слева
        self.ok_btn = InputField(10, win_h - 50, 60, 40)
        self.ok_btn.text = "OK"

        # кнопка CLEAR рядом
        self.clear_btn = InputField(80, win_h - 50, 120, 40)
        self.clear_btn.text = "CLEAR"

        self.screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
        pygame.display.set_caption(title)
        pygame.font.SysFont('Comic Sans MS', 36)
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
        self.done = False
        self.clock = pygame.time.Clock()

    def run(self):
        
        while not self.done:
            m_pos = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()


            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True
                    raise KeyboardInterrupt("GUI closed by user")

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    column = pos[0] // (self.width + 2)
                    row = pos[1] // (self.height + 2)
                    if row >= self.x_dim or column >= self.y_dim:
                        print("Clicked outside grid")
                        continue

                    if self.pending_start is None:
                        if any(pair[0] == (row, column) or pair[1] == (row, column) for pair in self.drone_pairs):
                            print("Это клетка уже используется.")
                            continue
                        self.pending_start = (row, column)
                        self.gui_grid[row][column] = [255, 0, 0]
                        print(f"Start position set to: {self.pending_start}")
                    else:
                        if self.pending_start == (row, column):
                            print("Цель не может совпадать со стартом.")
                            continue
                        if any(pair[0] == (row, column) or pair[1] == (row, column) for pair in self.drone_pairs):
                            print("Это клетка уже используется.")
                            continue
                        self.drone_pairs.append((self.pending_start, (row, column)))
                        self.gui_grid[row][column] = [0, 255, 0]
                        print(f"Added drone #{len(self.drone_pairs)}: start={self.pending_start}, goal={(row, column)}")
                        self.pending_start = None

            self.screen.fill((0, 0, 0))
            for row in range(self.gui_grid.shape[0]):
                for column in range(self.gui_grid.shape[1]):
                    color = self.gui_grid[row][column]
                    pygame.draw.rect(self.screen,
                                        color,
                                        [(self.width + 2) * column + 2,
                                        (self.height + 2) * row + 2,
                                        self.width,
                                        self.height])
                    

            okBtn_is_hovered = self.ok_btn.field.collidepoint(m_pos)
            clearBtn_is_hovered = self.clear_btn.field.collidepoint(m_pos)

            if okBtn_is_hovered and m_click[0]:  # Left mouse button
                print("Ok Button clicked!")
                if self.pending_start is not None:
                    print("Завершите текущий старт/цель или очистите выбор.")
                elif self.drone_pairs:
                    print(f"Sending {len(self.drone_pairs)} drone(s) to the server")
                    cw.send_points(self.drone_pairs)
                    self.done = True
                else:
                    print("Нет ни одного дрона для отправки.")

            if clearBtn_is_hovered and m_click[0]: 
                print("Clear Button clicked!")
                self.pending_start = None
                self.drone_pairs = []
                self.gui_grid = np.ones((self.x_dim, self.y_dim, 3), dtype=np.uint8) * 255

            ok_btn_text = self.font.render(self.ok_btn.text,True,(0,0,0))
            pygame.draw.rect(self.screen, self.ok_btn.clr_edit if okBtn_is_hovered else self.ok_btn.clr_lock, self.ok_btn.field)
            self.screen.blit(ok_btn_text, (self.ok_btn.x, self.ok_btn.y))
            
            clr_btn_text = self.font.render(self.clear_btn.text,True,(0,0,0))
            pygame.draw.rect(self.screen, self.clear_btn.clr_edit if clearBtn_is_hovered else self.clear_btn.clr_lock, self.clear_btn.field)
            self.screen.blit(clr_btn_text, (self.clear_btn.x, self.clear_btn.y))

            status_text = "Выберите старт для нового дрона" if self.pending_start is None else f"Выберите цель для дрона #{len(self.drone_pairs) + 1}"
            status_surface = self.small_font.render(status_text, True, (255, 255, 255))
            self.screen.blit(status_surface, (230, self.y_dim * (self.height + 2) + 10))

            pairs_text = f"Дронов: {len(self.drone_pairs)}"
            pairs_surface = self.small_font.render(pairs_text, True, (255, 255, 255))
            self.screen.blit(pairs_surface, (230, self.y_dim * (self.height + 2) + 35))

            self.clock.tick(60)
            pygame.display.flip()

if __name__ == "__main__":
    gui = GridGUI(x_dim=10, y_dim=10)
    gui.run()
    pygame.quit()