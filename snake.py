#!/usr/bin/env python3
"""Минимальная кроссплатформенная игра «Змейка» на tkinter (работает в Windows)."""

import random
import tkinter as tk
from tkinter import messagebox


CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
TICK_MS = 110


class SnakeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Snake")

        self.canvas = tk.Canvas(
            root,
            width=GRID_WIDTH * CELL_SIZE,
            height=GRID_HEIGHT * CELL_SIZE,
            bg="#111111",
            highlightthickness=0,
        )
        self.canvas.pack(padx=8, pady=8)

        self.score_var = tk.StringVar(value="Score: 0")
        self.score_label = tk.Label(root, textvariable=self.score_var, font=("Arial", 12))
        self.score_label.pack(pady=(0, 8))

        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        self.snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = (1, 0)
        self.pending_direction = self.direction
        self.score = 0
        self.running = True

        self.food = self.place_food()

        self.root.bind("<Up>", lambda _e: self.set_direction(0, -1))
        self.root.bind("<Down>", lambda _e: self.set_direction(0, 1))
        self.root.bind("<Left>", lambda _e: self.set_direction(-1, 0))
        self.root.bind("<Right>", lambda _e: self.set_direction(1, 0))

        self.root.bind("w", lambda _e: self.set_direction(0, -1))
        self.root.bind("s", lambda _e: self.set_direction(0, 1))
        self.root.bind("a", lambda _e: self.set_direction(-1, 0))
        self.root.bind("d", lambda _e: self.set_direction(1, 0))

        self.root.bind("q", lambda _e: self.end_game())
        self.root.bind("<Escape>", lambda _e: self.end_game())

        self.draw()
        self.tick()

    def set_direction(self, dx, dy):
        if not self.running:
            return

        curr_dx, curr_dy = self.direction
        if (dx, dy) == (-curr_dx, -curr_dy):
            return
        self.pending_direction = (dx, dy)

    def place_food(self):
        snake_set = set(self.snake)
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in snake_set:
                return pos

    def tick(self):
        if not self.running:
            return

        self.direction = self.pending_direction
        dx, dy = self.direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + dx, head_y + dy)

        out_of_bounds = (
            new_head[0] < 0
            or new_head[0] >= GRID_WIDTH
            or new_head[1] < 0
            or new_head[1] >= GRID_HEIGHT
        )
        hit_self = new_head in self.snake
        if out_of_bounds or hit_self:
            self.running = False
            self.draw()
            messagebox.showinfo("Game Over", f"Ты проиграл. Счет: {self.score}")
            self.root.destroy()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.score_var.set(f"Score: {self.score}")
            self.food = self.place_food()
        else:
            self.snake.pop()

        self.draw()
        self.root.after(TICK_MS, self.tick)

    def draw_cell(self, x, y, color):
        x1 = x * CELL_SIZE
        y1 = y * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#222222")

    def draw(self):
        self.canvas.delete("all")
        self.draw_cell(self.food[0], self.food[1], "#ffd166")

        for i, (x, y) in enumerate(self.snake):
            color = "#06d6a0" if i == 0 else "#118ab2"
            self.draw_cell(x, y, color)

    def end_game(self):
        self.running = False
        self.root.destroy()


if __name__ == "__main__":
    app = tk.Tk()
    SnakeGame(app)
    app.mainloop()
