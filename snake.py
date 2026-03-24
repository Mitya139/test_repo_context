#!/usr/bin/env python3
"""Прокачанная змейка на tkinter: бонусы, меню, история и сохранение рекордов."""

from __future__ import annotations

import json
import random
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone
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

HISTORY_PATH = Path(__file__).resolve().parent / "snake_history.json"
MAX_HISTORY_ITEMS = 30

BONUS_SPAWN_COOLDOWN = 9.0
BONUS_VISIBLE_SECONDS = 9.0


@dataclass(frozen=True)
class FruitType:
    key: str
    score: int


@dataclass(frozen=True)
class BonusType:
    key: str
    label: str
    duration: float
    color: str
    symbol: str


FRUIT_TYPES = [
    FruitType("apple", 1),
    FruitType("banana", 2),
    FruitType("grapes", 3),
    FruitType("strawberry", 4),
]

BONUS_TYPES = [
    BonusType("double", "x2 очки", 10.0, "#f4a261", "x2"),
    BonusType("ghost", "Фантом", 8.0, "#b28dff", "👻"),
    BonusType("slowmo", "Слоумо", 8.0, "#56cfe1", "⏱"),
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
        self.canvas.grid(row=0, column=0, columnspan=3)

        self.score_var = tk.StringVar(value="Score: 0")
        self.best_var = tk.StringVar(value="Best: 0")
        self.games_var = tk.StringVar(value="Games: 0")

        self.score_label = tk.Label(
            self.frame,
            textvariable=self.score_var,
            fg="#e9eef9",
            bg="#111318",
            font=("Segoe UI", 12, "bold"),
        )
        self.score_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.best_label = tk.Label(
            self.frame,
            textvariable=self.best_var,
            fg="#a8b4cc",
            bg="#111318",
            font=("Segoe UI", 11),
        )
        self.best_label.grid(row=1, column=1, sticky="e", pady=(8, 0))

        self.games_label = tk.Label(
            self.frame,
            textvariable=self.games_var,
            fg="#8da0be",
            bg="#111318",
            font=("Segoe UI", 11),
        )
        self.games_label.grid(row=1, column=2, sticky="e", pady=(8, 0), padx=(10, 0))

        self.fruit_images = self._build_fruit_images()
        self.fruit_fallback_colors = {
            "apple": "#ff5c5c",
            "banana": "#ffd166",
            "grapes": "#9d6bff",
            "strawberry": "#ff4d88",
        }

        history = self._load_history()
        self.best_score = int(history.get("best_score", 0))
        self.games_played = int(history.get("games_played", 0))
        self.history: list[dict] = list(history.get("history", []))

        self.best_var.set(f"Best: {self.best_score}")
        self.games_var.set(f"Games: {self.games_played}")

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

        self.active_bonuses: dict[str, float] = {}
        self.bonus_pos: tuple[int, int] | None = None
        self.bonus_type: BonusType | None = None
        self.bonus_spawn_at = time.perf_counter() + BONUS_SPAWN_COOLDOWN
        self.bonus_expire_at: float | None = None

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

    def _load_history(self) -> dict:
        if not HISTORY_PATH.exists():
            return {"best_score": 0, "games_played": 0, "history": []}

        try:
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"best_score": 0, "games_played": 0, "history": []}

        if not isinstance(data, dict):
            return {"best_score": 0, "games_played": 0, "history": []}

        return {
            "best_score": int(data.get("best_score", 0)),
            "games_played": int(data.get("games_played", 0)),
            "history": data.get("history", []),
        }

    def _save_history(self):
        data = {
            "best_score": self.best_score,
            "games_played": self.games_played,
            "history": self.history[-MAX_HISTORY_ITEMS:],
        }
        HISTORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _register_game_result(self):
        self.games_played += 1
        self.best_score = max(self.best_score, self.score)
        self.best_var.set(f"Best: {self.best_score}")
        self.games_var.set(f"Games: {self.games_played}")

        self.history.append(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "score": self.score,
                "length": len(self.snake),
            }
        )
        self._save_history()

    def _build_fruit_images(self) -> dict[str, tk.PhotoImage]:
        """Создаёт маленькие pixel-art фрукты в памяти (без файлов на диске)."""
        palette = {
            "R": "#dd3b3b",
            "Y": "#ffd166",
            "P": "#8c5bff",
            "S": "#ff4d88",
            "G": "#32c26b",
            "B": "#7f4d2a",
            "W": "#fef3c7",
        }

        sprites = {
            "apple": [
                "................",
                ".......B........",
                "......GGG.......",
                ".....RRRRR......",
                "....RRRRRRR.....",
                "....RRRRRRR.....",
                "...RRRRRRRRR....",
                "...RRRRRRRRR....",
                "...RRRRRRRRR....",
                "....RRRRRRR.....",
                "....RRRRRRR.....",
                ".....RRRRR......",
                "................",
                "................",
                "................",
                "................",
            ],
            "banana": [
                "................",
                "................",
                "..........YY....",
                "........YYYY....",
                "......YYYYY.....",
                ".....YYYYY......",
                "....YYYYY.......",
                "...YYYYY........",
                "..YYYYY.........",
                ".YYYYY..........",
                ".YYYY...........",
                "..YY............",
                "................",
                "................",
                "................",
                "................",
            ],
            "grapes": [
                ".......B........",
                "......GG........",
                ".....PPP........",
                "....PPPPP.......",
                "...PPPPPPP......",
                "....PPPPP.......",
                "...PPPPPPP......",
                "....PPPPP.......",
                "...PPPPPPP......",
                "....PPPPP.......",
                ".....PPP........",
                "................",
                "................",
                "................",
                "................",
                "................",
            ],
            "strawberry": [
                "......GGGG......",
                ".....GGGGGG.....",
                "......GGGG......",
                "......SSSS......",
                ".....SSSSSS.....",
                "....SSWSSWSS....",
                "....SSSSSSSS....",
                "....SWSSWSSS....",
                ".....SSSSSS.....",
                ".....SSWSSS.....",
                "......SSSS......",
                ".......SS.......",
                "................",
                "................",
                "................",
                "................",
            ],
        }

        images: dict[str, tk.PhotoImage] = {}
        for key, rows in sprites.items():
            base = tk.PhotoImage(width=16, height=16)
            for y, row in enumerate(rows):
                for x, ch in enumerate(row):
                    if ch in palette:
                        base.put(palette[ch], (x, y))
            zoom = max(1, CELL_SIZE // 16)
            images[key] = base.zoom(zoom, zoom)
        return images

    def queue_direction(self, direction: tuple[int, int]):
        if self.state != "running":
            return

        current = self.pending_inputs[-1] if self.pending_inputs else self.direction
        if direction == current or direction == (-current[0], -current[1]):
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

        self.active_bonuses = {}
        self.bonus_pos = None
        self.bonus_type = None
        self.bonus_expire_at = None
        self.bonus_spawn_at = time.perf_counter() + BONUS_SPAWN_COOLDOWN

        self.spawn_food()
        self.last_time = time.perf_counter()
        self.accumulator = 0.0
        self.draw_scene()

    def show_menu(self):
        if self.state == "running":
            self.state = "menu"
        self.draw_scene()

    def spawn_food(self):
        occupied = set(self.snake)
        if self.bonus_pos is not None:
            occupied.add(self.bonus_pos)

        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in occupied:
                self.food_pos = pos
                self.food_type = random.choice(FRUIT_TYPES)
                return

    def try_spawn_bonus(self, now: float):
        if self.bonus_pos is not None:
            return
        if now < self.bonus_spawn_at:
            return

        occupied = set(self.snake)
        occupied.add(self.food_pos)
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in occupied:
                self.bonus_pos = pos
                self.bonus_type = random.choice(BONUS_TYPES)
                self.bonus_expire_at = now + BONUS_VISIBLE_SECONDS
                return

    def activate_bonus(self, bonus: BonusType, now: float):
        self.active_bonuses[bonus.key] = now + bonus.duration

    def update_bonuses(self, now: float):
        expired = [key for key, expire_at in self.active_bonuses.items() if now >= expire_at]
        for key in expired:
            del self.active_bonuses[key]

        if self.bonus_pos is not None and self.bonus_expire_at is not None and now >= self.bonus_expire_at:
            self.bonus_pos = None
            self.bonus_type = None
            self.bonus_expire_at = None
            self.bonus_spawn_at = now + BONUS_SPAWN_COOLDOWN

    def game_loop(self):
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now

        if self.state == "running":
            self.update_bonuses(now)
            self.try_spawn_bonus(now)

            effective_interval = self.move_interval
            if "slowmo" in self.active_bonuses:
                effective_interval *= 1.55

            self.accumulator += dt
            while self.accumulator >= effective_interval:
                self.accumulator -= effective_interval
                self.step(now)
                if self.state != "running":
                    break

        self.root.after(int(1000 / FPS), self.game_loop)

    def step(self, now: float):
        if self.pending_inputs:
            self.direction = self.pending_inputs.pop(0)

        dx, dy = self.direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + dx, head_y + dy)

        ghost_active = "ghost" in self.active_bonuses
        if ghost_active:
            new_head = (new_head[0] % GRID_WIDTH, new_head[1] % GRID_HEIGHT)

        out_of_bounds = not (0 <= new_head[0] < GRID_WIDTH and 0 <= new_head[1] < GRID_HEIGHT)
        hit_self = new_head in self.snake

        if (out_of_bounds or hit_self) and not ghost_active:
            self.state = "game_over"
            self._register_game_result()
            self.draw_scene()
            return

        self.snake.insert(0, new_head)

        if self.bonus_pos is not None and new_head == self.bonus_pos and self.bonus_type is not None:
            self.activate_bonus(self.bonus_type, now)
            self.bonus_pos = None
            self.bonus_type = None
            self.bonus_expire_at = None
            self.bonus_spawn_at = now + BONUS_SPAWN_COOLDOWN

        if new_head == self.food_pos:
            points = self.food_type.score
            if "double" in self.active_bonuses:
                points *= 2

            self.score += points
            self.score_var.set(f"Score: {self.score}")
            self.move_interval = max(MIN_MOVE_INTERVAL, self.move_interval - SPEEDUP_PER_POINT * points)
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

    def draw_bonus(self):
        if self.bonus_pos is None or self.bonus_type is None:
            return

        bx, by = self.bonus_pos
        x = bx * CELL_SIZE + CELL_SIZE // 2
        y = by * CELL_SIZE + CELL_SIZE // 2

        self.canvas.create_oval(
            x - CELL_SIZE // 2 + 3,
            y - CELL_SIZE // 2 + 3,
            x + CELL_SIZE // 2 - 3,
            y + CELL_SIZE // 2 - 3,
            fill=self.bonus_type.color,
            outline="#ffffff",
            width=1,
        )
        self.canvas.create_text(x, y, text=self.bonus_type.symbol, fill="#101318", font=("Segoe UI Emoji", 11, "bold"))

    def draw_active_bonuses(self):
        if not self.active_bonuses:
            return

        now = time.perf_counter()
        labels = []
        for bonus in BONUS_TYPES:
            if bonus.key in self.active_bonuses:
                left = max(0.0, self.active_bonuses[bonus.key] - now)
                labels.append(f"{bonus.label}: {left:0.1f}s")

        if not labels:
            return

        self.canvas.create_rectangle(8, 8, 260, 8 + 22 * len(labels), fill="#000000", outline="#3f4b63", stipple="gray50")
        for i, text in enumerate(labels):
            self.canvas.create_text(16, 18 + 22 * i, anchor="w", text=text, fill="#d8dfef", font=("Segoe UI", 10, "bold"))

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

        self.draw_bonus()

        for i, (sx, sy) in enumerate(self.snake):
            color = "#63ff94" if i == 0 else "#24b1d1"
            if "ghost" in self.active_bonuses:
                color = "#b28dff" if i == 0 else "#9aa0ff"
            self.draw_cell_rect(sx, sy, color)

        self.draw_active_bonuses()

    def draw_overlay(self, title: str, lines: list[str]):
        cx = BOARD_WIDTH // 2
        cy = BOARD_HEIGHT // 2
        self.canvas.create_rectangle(
            cx - 230,
            cy - 125,
            cx + 230,
            cy + 125,
            fill="#000000",
            outline="#5c6a82",
            width=2,
            stipple="gray50",
        )
        self.canvas.create_text(
            cx,
            cy - 75,
            text=title,
            fill="#f8f9ff",
            font=("Segoe UI", 24, "bold"),
        )

        for idx, line in enumerate(lines):
            self.canvas.create_text(
                cx,
                cy - 20 + idx * 28,
                text=line,
                fill="#d8dfef",
                font=("Segoe UI", 13),
            )

    def _history_preview(self) -> list[str]:
        preview = []
        for item in self.history[-3:][::-1]:
            score = item.get("score", 0)
            stamp = item.get("time", "")
            preview.append(f"{stamp[:19].replace('T', ' ')} | {score}")
        return preview

    def draw_scene(self):
        self.draw_board()
        if self.state == "menu":
            lines = [
                "Enter — начать игру",
                "Стрелки / WASD — управление",
                "R — рестарт, Esc — в меню",
                "Бонусы: x2 очки, Фантом, Слоумо",
                f"Лучший счет: {self.best_score} | Игр: {self.games_played}",
            ]
            lines.extend(self._history_preview() or ["История пока пустая"])
            self.draw_overlay("SUPER SNAKE", lines)
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
