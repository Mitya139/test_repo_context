#!/usr/bin/env python3
"""Прокачанная змейка на tkinter: меню, быстрый отклик, разные фрукты и переигровка."""

from __future__ import annotations

import random
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path


CELL_SIZE = 24
GRID_WIDTH = 28
GRID_HEIGHT = 20
BOARD_WIDTH = GRID_WIDTH * CELL_SIZE
BOARD_HEIGHT = GRID_HEIGHT * CELL_SIZE

FPS = 60
INITIAL_MOVE_INTERVAL = 0.11
MIN_MOVE_INTERVAL = 0.055
SPEEDUP_PER_POINT = 0.002

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "fruits"


@dataclass(frozen=True)
class FruitType:
    key: str
    score: int


FRUIT_TYPES = [
    FruitType("apple", 1),
    FruitType("banana", 2),
    FruitType("grapes", 3),
    FruitType("strawberry", 4),
]


class SnakeGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Super Snake")
        self.root.resizable(False, False)

        self.frame = tk.Frame(root, bg="#111318")
        self.frame.pack(padx=10, pady=10)

        self.canvas = tk.Canvas(
            self.frame,
            width=BOARD_WIDTH,
            height=BOARD_HEIGHT,
            bg="#0f1320",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, columnspan=2)

        self.score_var = tk.StringVar(value="Score: 0")
        self.best_var = tk.StringVar(value="Best: 0")

        self.score_label = tk.Label(self.frame, textvariable=self.score_var, fg="#e9eef9", bg="#111318", font=("Segoe UI", 12, "bold"))
        self.score_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.best_label = tk.Label(self.frame, textvariable=self.best_var, fg="#a8b4cc", bg="#111318", font=("Segoe UI", 11))
        self.best_label.grid(row=1, column=1, sticky="e", pady=(8, 0))

        self.fruit_images = self._load_fruit_images()
        self.fruit_fallback_colors = {
            "apple": "#ff5c5c",
            "banana": "#ffd166",
            "grapes": "#9d6bff",
            "strawberry": "#ff4d88",
        }

        self.best_score = 0
        self.state = "menu"  # menu | running | game_over

        self.snake: list[tuple[int, int]] = []
        self.direction = (1, 0)
        self.pending_inputs: list[tuple[int, int]] = []
        self.food_pos = (0, 0)
        self.food_type = FRUIT_TYPES[0]
        self.score = 0
        self.move_interval = INITIAL_MOVE_INTERVAL

        self.last_time = time.perf_counter()
        self.accumulator = 0.0

        self.root.bind("<Up>", lambda _e: self.queue_direction((0, -1)))
        self.root.bind("<Down>", lambda _e: self.queue_direction((0, 1)))
        self.root.bind("<Left>", lambda _e: self.queue_direction((-1, 0)))
        self.root.bind("<Right>", lambda _e: self.queue_direction((1, 0)))
        self.root.bind("w", lambda _e: self.queue_direction((0, -1)))
        self.root.bind("s", lambda _e: self.queue_direction((0, 1)))
        self.root.bind("a", lambda _e: self.queue_direction((-1, 0)))
        self.root.bind("d", lambda _e: self.queue_direction((1, 0)))

        self.root.bind("<Return>", lambda _e: self.handle_enter())
        self.root.bind("r", lambda _e: self.restart_game())
        self.root.bind("<Escape>", lambda _e: self.show_menu())

        self.draw_scene()
        self.game_loop()

    def _load_fruit_images(self) -> dict[str, tk.PhotoImage]:
        images: dict[str, tk.PhotoImage] = {}
        for fruit in FRUIT_TYPES:
            path = ASSETS_DIR / f"{fruit.key}.ppm"
            if path.exists():
                img = tk.PhotoImage(file=str(path))
                zoom = max(1, CELL_SIZE // max(1, img.width()))
                if zoom > 1:
                    img = img.zoom(zoom, zoom)
                images[fruit.key] = img
        return images

    def queue_direction(self, direction: tuple[int, int]):
        if self.state != "running":
            return

        current = self.pending_inputs[-1] if self.pending_inputs else self.direction
        if direction == current:
            return
        if direction == (-current[0], -current[1]):
            return

        if len(self.pending_inputs) < 3:
            self.pending_inputs.append(direction)

    def handle_enter(self):
        if self.state in {"menu", "game_over"}:
            self.restart_game()

    def restart_game(self):
        self.state = "running"
        mid_x = GRID_WIDTH // 2
        mid_y = GRID_HEIGHT // 2
        self.snake = [(mid_x, mid_y), (mid_x - 1, mid_y), (mid_x - 2, mid_y)]
        self.direction = (1, 0)
        self.pending_inputs = []

        self.score = 0
        self.score_var.set("Score: 0")
        self.move_interval = INITIAL_MOVE_INTERVAL

        self.spawn_food()
        self.last_time = time.perf_counter()
        self.accumulator = 0.0
        self.draw_scene()

    def show_menu(self):
        if self.state == "running":
            self.state = "menu"
        self.draw_scene()

    def spawn_food(self):
        snake_set = set(self.snake)
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in snake_set:
                self.food_pos = pos
                self.food_type = random.choice(FRUIT_TYPES)
                return

    def game_loop(self):
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now

        if self.state == "running":
            self.accumulator += dt
            while self.accumulator >= self.move_interval:
                self.accumulator -= self.move_interval
                self.step()
                if self.state != "running":
                    break

        self.root.after(int(1000 / FPS), self.game_loop)

    def step(self):
        if self.pending_inputs:
            self.direction = self.pending_inputs.pop(0)

        dx, dy = self.direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + dx, head_y + dy)

        out_of_bounds = not (0 <= new_head[0] < GRID_WIDTH and 0 <= new_head[1] < GRID_HEIGHT)
        hit_self = new_head in self.snake
        if out_of_bounds or hit_self:
            self.state = "game_over"
            self.best_score = max(self.best_score, self.score)
            self.best_var.set(f"Best: {self.best_score}")
            self.draw_scene()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food_pos:
            self.score += self.food_type.score
            self.score_var.set(f"Score: {self.score}")
            self.move_interval = max(MIN_MOVE_INTERVAL, self.move_interval - SPEEDUP_PER_POINT * self.food_type.score)
            self.spawn_food()
        else:
            self.snake.pop()

        self.draw_scene()

    def draw_cell_rect(self, x: int, y: int, color: str):
        x1 = x * CELL_SIZE
        y1 = y * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#1a2030")

    def draw_board(self):
        self.canvas.delete("all")

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                tile = "#101728" if (x + y) % 2 == 0 else "#0d1422"
                self.draw_cell_rect(x, y, tile)

        fx, fy = self.food_pos
        if self.food_type.key in self.fruit_images:
            self.canvas.create_image(
                fx * CELL_SIZE + CELL_SIZE // 2,
                fy * CELL_SIZE + CELL_SIZE // 2,
                image=self.fruit_images[self.food_type.key],
            )
        else:
            self.draw_cell_rect(fx, fy, self.fruit_fallback_colors[self.food_type.key])

        for i, (sx, sy) in enumerate(self.snake):
            color = "#38ef7d" if i == 0 else "#24b1d1"
            self.draw_cell_rect(sx, sy, color)

    def draw_overlay(self, title: str, lines: list[str]):
        cx = BOARD_WIDTH // 2
        cy = BOARD_HEIGHT // 2
        self.canvas.create_rectangle(cx - 220, cy - 120, cx + 220, cy + 120, fill="#000000", outline="#5c6a82", width=2, stipple="gray50")
        self.canvas.create_text(cx, cy - 70, text=title, fill="#f8f9ff", font=("Segoe UI", 24, "bold"))

        for idx, line in enumerate(lines):
            self.canvas.create_text(cx, cy - 15 + idx * 28, text=line, fill="#d8dfef", font=("Segoe UI", 13))

    def draw_scene(self):
        self.draw_board()
        if self.state == "menu":
            self.draw_overlay(
                "SUPER SNAKE",
                [
                    "Enter — начать игру",
                    "Стрелки / WASD — управление",
                    "Esc — вернуться в меню",
                    "R — рестарт во время игры",
                ],
            )
        elif self.state == "game_over":
            self.draw_overlay(
                "GAME OVER",
                [
                    f"Счет: {self.score}   Лучший: {self.best_score}",
                    "Enter — сыграть снова",
                    "Esc — в меню",
                ],
            )


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
