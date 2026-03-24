#!/usr/bin/env python3
"""Минимальная игра «Змейка» в терминале (curses)."""

import curses
import random
import time


def place_food(height, width, snake_set):
    while True:
        food = (random.randint(1, height - 2), random.randint(1, width - 2))
        if food not in snake_set:
            return food


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(120)
    stdscr.keypad(True)

    height, width = stdscr.getmaxyx()
    if height < 10 or width < 20:
        stdscr.clear()
        stdscr.addstr(0, 0, "Окно слишком маленькое. Нужно минимум 20x10.")
        stdscr.refresh()
        stdscr.getch()
        return

    snake = [(height // 2, width // 2), (height // 2, width // 2 - 1), (height // 2, width // 2 - 2)]
    snake_set = set(snake)
    direction = (0, 1)
    food = place_food(height, width, snake_set)
    score = 0

    key_to_dir = {
        curses.KEY_UP: (-1, 0),
        curses.KEY_DOWN: (1, 0),
        curses.KEY_LEFT: (0, -1),
        curses.KEY_RIGHT: (0, 1),
        ord("w"): (-1, 0),
        ord("s"): (1, 0),
        ord("a"): (0, -1),
        ord("d"): (0, 1),
    }

    while True:
        stdscr.erase()
        stdscr.border()
        stdscr.addstr(0, 2, f" Snake | Score: {score} ")
        stdscr.addch(food[0], food[1], "*")

        for i, (y, x) in enumerate(snake):
            stdscr.addch(y, x, "@" if i == 0 else "o")

        stdscr.refresh()

        key = stdscr.getch()
        if key == ord("q"):
            break

        if key in key_to_dir:
            new_dir = key_to_dir[key]
            if (new_dir[0] != -direction[0]) or (new_dir[1] != -direction[1]):
                direction = new_dir

        head_y, head_x = snake[0]
        new_head = (head_y + direction[0], head_x + direction[1])

        hit_wall = new_head[0] in (0, height - 1) or new_head[1] in (0, width - 1)
        hit_self = new_head in snake_set
        if hit_wall or hit_self:
            break

        snake.insert(0, new_head)
        snake_set.add(new_head)

        if new_head == food:
            score += 1
            food = place_food(height, width, snake_set)
        else:
            tail = snake.pop()
            snake_set.remove(tail)

        time.sleep(0.02)

    stdscr.nodelay(False)
    stdscr.addstr(height // 2, max(2, width // 2 - 8), f"Game Over! Score: {score}")
    stdscr.addstr(height // 2 + 1, max(2, width // 2 - 12), "Нажми любую клавишу...")
    stdscr.refresh()
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
