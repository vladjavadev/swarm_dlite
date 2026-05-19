import pygame
from client import client_websocket as cw
from utils.connect_dto import Connection as con
import time
import threading

def check_loop(gui):
    while gui.running:
        cw.get_connection(cw.con)
        time.sleep(0.5)


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


class GUI_ConnectServer:
    def __init__(self, 
                 title="Connect Server", 
                 width=400, 
                 height=400):
        self.width = width
        self.height = height
        self.cell_unit = None
        self.x_dim = None
        self.y_dim = None
        self.text=cw.con.get_status()
        self.rect = pygame.Rect(50,230,200,150)
        self.running = True

        pygame.init()
        win_w, win_h = window_size = [width,height]
        self.screen = pygame.display.set_mode(window_size)
        self.input_dim_x = InputField(80,80,80,80)
        self.input_dim_y  = InputField(220,80,80,80)
        self.input_unit = InputField(150,220,80,40)
        self.ok_btn = InputField(10, win_h - 50, 60, 40)
        self.ok_btn.text = "OK"

        # кнопка CLEAR рядом
        self.clear_btn = InputField(80, win_h - 50, 120, 40)
        self.clear_btn.text = "CLEAR"

        pygame.display.set_caption(title)
        pygame.font.SysFont('Comic Sans MS', 36)
        self.font = pygame.font.Font(None, 48)

        self.clock = pygame.time.Clock()


    def wr_text(self,field:InputField,event):
        if event.key == pygame.K_RETURN:
            print(f"Введено: {field.text}")
            field.text = ''
        elif event.key == pygame.K_BACKSPACE:
            field.text = field.text[:-1]
        else:
            if event.unicode.isdigit():
                field.text += event.unicode
    def input_dim(self):
        in_x = self.input_dim_x
        in_y = self.input_dim_y
        in_unit = self.input_unit
        ok_btn = self.ok_btn
        clr_btn = self.clear_btn
        
        click_handled = False  # Флаг для обработки одного клика

        while self.running:
            m_pos = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    raise KeyboardInterrupt("GUI closed by user")
                    
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if in_x.field.collidepoint(m_pos):
                        in_x.active = True
                        in_y.active = False
                        in_unit.active = False
                    elif in_y.field.collidepoint(m_pos):
                        in_y.active = True
                        in_x.active = False
                        in_unit.active = False
                    elif in_unit.field.collidepoint(m_pos):
                        in_unit.active = True
                        in_x.active = False
                        in_y.active = False
                    elif ok_btn.field.collidepoint(m_pos):
                        print("Ok Button clicked!")
                        if in_x.text.isdigit() and in_y.text.isdigit():
                            self.x_dim = int(in_x.text)
                            self.y_dim = int(in_y.text)
                            self.cell_unit = int(in_unit.text)

                            print(f"Grid Dimension: {self.x_dim}, Goal: {self.y_dim}")
                            cw.dim_grid.x_dim=self.x_dim
                            cw.dim_grid.y_dim=self.y_dim
                            
                            cw.send_dim_grid((self.x_dim, self.y_dim), self.cell_unit)
                            self.running = False
                            return  # Выходим из метода
                    elif clr_btn.field.collidepoint(m_pos):
                        print("Clear Button clicked!")
                        in_x.text = ''
                        in_y.text = ''
                        in_unit.text = ''
                    else:
                        in_x.active = False
                        in_y.active = False
                    
                    in_x.color = in_x.clr_edit if in_x.active else in_x.clr_lock
                    in_y.color = in_y.clr_edit if in_y.active else in_y.clr_lock
                    in_unit.color = in_unit.clr_edit if in_unit.active else in_unit.clr_lock
                    
                elif event.type == pygame.KEYDOWN:
                    if in_x.active:
                        self.wr_text(in_x, event)
                    elif in_y.active:
                        self.wr_text(in_y, event)
                    elif in_unit.active:
                        self.wr_text(in_unit, event)

            self.screen.fill((255, 255, 255))
            
            # Рисуем поля ввода
            pygame.draw.rect(self.screen, in_x.color, in_x.field)
            pygame.draw.rect(self.screen, in_y.color, in_y.field)
            pygame.draw.rect(self.screen, in_unit.color, in_unit.field)
            
            text_inputX = self.font.render(in_x.text, True, (0, 0, 0))
            text_inputY = self.font.render(in_y.text, True, (0, 0, 0))
            text_unit = self.font.render(in_unit.text, True, (0, 0, 0))
            
            self.screen.blit(text_inputX, (in_x.x, in_x.y + 20))
            self.screen.blit(text_inputY, (in_y.x, in_y.y + 20))
            self.screen.blit(text_unit, (in_unit.x, in_unit.y + 5))

            label_X = self.font.render("Dim X", True, (0, 0, 0))
            label_Y = self.font.render("Dim Y", True, (0, 0, 0))
            label_unit = self.font.render("Unit", True, (0, 0, 0))

            self.screen.blit(label_X, (in_x.x, in_x.y-50))
            self.screen.blit(label_Y, (in_y.x, in_y.y-50)) 
            self.screen.blit(label_unit, (in_unit.x, in_unit.y-50))
            # Рисуем кнопки
            okBtn_is_hovered = ok_btn.field.collidepoint(m_pos)
            clearBtn_is_hovered = clr_btn.field.collidepoint(m_pos)

            ok_btn_text = self.font.render(self.ok_btn.text, True, (0, 0, 0))
            pygame.draw.rect(self.screen, self.ok_btn.clr_edit if okBtn_is_hovered else self.ok_btn.clr_lock, self.ok_btn.field)
            self.screen.blit(ok_btn_text, (self.ok_btn.x + 10, self.ok_btn.y + 5))
            
            clr_btn_text = self.font.render(self.clear_btn.text, True, (0, 0, 0))
            pygame.draw.rect(self.screen, self.clear_btn.clr_edit if clearBtn_is_hovered else self.clear_btn.clr_lock, self.clear_btn.field)
            self.screen.blit(clr_btn_text, (self.clear_btn.x + 10, self.clear_btn.y + 5))
            
            self.clock.tick(30)
            pygame.display.flip()


    def run_game(self):
        thread = threading.Thread(target=check_loop, daemon=True, args=(self,))
        thread.start()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    raise KeyboardInterrupt("GUI closed by user")

            status = cw.con.get_status()
            if status == "connected":
                self.input_dim()  # Этот метод сам завершится при нажатии OK
                break  # Выходим из цикла

            self.screen.fill((255, 255, 255))
            text_connection = self.font.render(status, True, (0, 0, 0))
            self.screen.blit(text_connection, (self.rect.x, self.rect.y))
            pygame.draw.rect(self.screen, (0, 0, 0), self.rect, 2)
            self.clock.tick(30)
            pygame.display.flip()


