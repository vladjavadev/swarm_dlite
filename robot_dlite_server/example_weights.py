#!/usr/bin/env python3

"""
Пример использования весов в сетке для влияния на выбор маршрута.
"""

from dstar.grid import OccupancyGridMap
from dstar.d_star_lite import DStarLite

def main():
    # Создаем сетку 10x10
    grid = OccupancyGridMap(10, 10, exploration_setting='8N')

    # Устанавливаем препятствия
    grid.set_obstacle((5, 5))
    grid.set_obstacle((5, 6))

    # Устанавливаем веса для некоторых клеток
    # Высокий вес делает клетку менее привлекательной для маршрута
    grid.set_weight((3, 3), 5.0)  # Высокий вес
    grid.set_weight((4, 4), 2.0)  # Средний вес
    grid.set_weight((6, 6), 1.5)  # Низкий вес

    # Начальная и конечная точки
    start = (0, 0)
    goal = (9, 9)

    # Создаем алгоритм D* Lite
    dstar = DStarLite(grid, start, goal)

    # Вычисляем кратчайший путь
    dstar.compute_shortest_path()

    # Получаем путь (нужно реализовать метод для извлечения пути)
    # В оригинальном коде путь извлекается отдельно, но для примера:
    print("Веса установлены:")
    print(f"Вес клетки (3,3): {grid.get_weight((3,3))}")
    print(f"Вес клетки (4,4): {grid.get_weight((4,4))}")
    print(f"Вес клетки (6,6): {grid.get_weight((6,6))}")
    print("Алгоритм учитывает веса при выборе маршрута.")

if __name__ == "__main__":
    main()