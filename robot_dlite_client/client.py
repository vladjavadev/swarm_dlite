from client import grid_gui,gui_init,gui_conect_server
from client import client_websocket as cw
import time
import sys

if __name__ == "__main__":
    try:
        connect_gui = gui_conect_server.GUI_ConnectServer()
        connect_gui.run_game()
        width = 600
        height = 600
        dim = (cw.dim_grid.x_dim, cw.dim_grid.y_dim)

        cell_width = width//dim[0]
        cell_height = height//dim[0]
        time.sleep(0.2)  # Небольшая пауза перед запуском основной GUI
        init_gui = gui_init.GridGUI(width=cell_width,height=cell_height,x_dim=dim[0], y_dim=dim[1])
        init_gui.run() 
        # cw.send_dim_grid(dim)
        # cw.send_points((0,0),(9,9))
        time.sleep(0.2)  # Небольшая пауза перед запуском основной GUI
        cell_size = 200
        main_gui = grid_gui.Animation(width=cell_width,height=cell_height,x_dim=dim[0], y_dim=dim[1],cell_size=cell_size)
        main_gui.run_game()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем") 