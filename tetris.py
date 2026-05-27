#!/usr/bin/env python3
"""
Tetris — pure Python, zero dependencies.
Run:  python tetris.py
"""

import tkinter as tk
import random

# ── constants ──────────────────────────────────────────────────────────────────
COLS, ROWS = 10, 20
CELL       = 34          # px per cell
SIDEBAR    = 200         # right panel width
WIDTH      = COLS * CELL
HEIGHT     = ROWS * CELL
FPS        = 60
LOCK_DELAY = 500         # ms before a grounded piece locks

COLORS = {
    "I": "#00ECFF",
    "O": "#FFE600",
    "T": "#CC44FF",
    "S": "#44FF77",
    "Z": "#FF4455",
    "J": "#4477FF",
    "L": "#FF9900",
    "ghost": "#FFFFFF",
    "bg":    "#0D0D14",
    "grid":  "#1A1A2E",
    "panel": "#13131F",
    "text":  "#E0E0FF",
    "accent":"#00ECFF",
}

TETROMINOES = {
    "I": [[(0,1),(1,1),(2,1),(3,1)],
          [(2,0),(2,1),(2,2),(2,3)],
          [(0,2),(1,2),(2,2),(3,2)],
          [(1,0),(1,1),(1,2),(1,3)]],
    "O": [[(1,0),(2,0),(1,1),(2,1)]]*4,
    "T": [[(0,1),(1,1),(2,1),(1,0)],
          [(1,0),(1,1),(1,2),(2,1)],
          [(0,1),(1,1),(2,1),(1,2)],
          [(1,0),(1,1),(1,2),(0,1)]],
    "S": [[(1,0),(2,0),(0,1),(1,1)],
          [(1,0),(1,1),(2,1),(2,2)],
          [(1,1),(2,1),(0,2),(1,2)],
          [(0,0),(0,1),(1,1),(1,2)]],
    "Z": [[(0,0),(1,0),(1,1),(2,1)],
          [(2,0),(1,1),(2,1),(1,2)],
          [(0,1),(1,1),(1,2),(2,2)],
          [(1,0),(0,1),(1,1),(0,2)]],
    "J": [[(0,0),(0,1),(1,1),(2,1)],
          [(1,0),(2,0),(1,1),(1,2)],
          [(0,1),(1,1),(2,1),(2,2)],
          [(1,0),(1,1),(0,2),(1,2)]],
    "L": [[(2,0),(0,1),(1,1),(2,1)],
          [(1,0),(1,1),(1,2),(2,2)],
          [(0,1),(1,1),(2,1),(0,2)],
          [(0,0),(1,0),(1,1),(1,2)]],
}

LEVEL_SPEEDS = [800,700,600,500,400,320,250,190,140,100,80,60,50,40,30]
POINTS = [0, 100, 300, 500, 800]   # 0-4 lines cleared


# ── helpers ───────────────────────────────────────────────────────────────────
def piece_cells(shape, rot, x, y):
    return [(x + dx, y + dy) for dx, dy in TETROMINOES[shape][rot % len(TETROMINOES[shape])]]


# ── game logic ────────────────────────────────────────────────────────────────
class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board   = [[None]*COLS for _ in range(ROWS)]
        self.score   = 0
        self.lines   = 0
        self.level   = 1
        self.over    = False
        self.paused  = False
        self.bag     = []
        self.next    = self._next_piece()
        self._spawn()

    def _next_piece(self):
        if not self.bag:
            self.bag = list(TETROMINOES.keys()) * 2
            random.shuffle(self.bag)
        return self.bag.pop()

    def _spawn(self):
        self.shape = self.next
        self.next  = self._next_piece()
        self.rot   = 0
        self.x     = COLS // 2 - 2
        self.y     = 0
        self.lock_timer = None
        if not self._valid(self.x, self.y, self.rot):
            self.over = True

    def _valid(self, x, y, rot):
        for cx, cy in piece_cells(self.shape, rot, x, y):
            if cx < 0 or cx >= COLS or cy >= ROWS:
                return False
            if cy >= 0 and self.board[cy][cx]:
                return False
        return True

    def move(self, dx):
        if self._valid(self.x + dx, self.y, self.rot):
            self.x += dx

    def rotate(self, d=1):
        new_rot = (self.rot + d) % len(TETROMINOES[self.shape])
        for kick in [0, 1, -1, 2, -2]:
            if self._valid(self.x + kick, self.y, new_rot):
                self.x   += kick
                self.rot  = new_rot
                return

    def soft_drop(self):
        if self._valid(self.x, self.y + 1, self.rot):
            self.y     += 1
            self.score += 1
            return True
        return False

    def hard_drop(self):
        while self._valid(self.x, self.y + 1, self.rot):
            self.y     += 1
            self.score += 2
        self._lock()

    def ghost_y(self):
        gy = self.y
        while self._valid(self.x, gy + 1, self.rot):
            gy += 1
        return gy

    def gravity(self):
        """Called by the game loop every tick. Returns True if piece moved."""
        if not self._valid(self.x, self.y + 1, self.rot):
            return False   # caller handles lock delay
        self.y += 1
        return True

    def _lock(self):
        for cx, cy in piece_cells(self.shape, self.rot, self.x, self.y):
            if 0 <= cy < ROWS:
                self.board[cy][cx] = self.shape
        cleared = self._clear_lines()
        self.score += POINTS[cleared] * self.level
        self.lines += cleared
        self.level  = min(15, self.lines // 10 + 1)
        self._spawn()

    def _clear_lines(self):
        full   = [r for r in range(ROWS) if all(self.board[r])]
        for r in full:
            del self.board[r]
            self.board.insert(0, [None]*COLS)
        return len(full)

    def tick_speed(self):
        return LEVEL_SPEEDS[min(self.level - 1, len(LEVEL_SPEEDS)-1)]


# ── UI ─────────────────────────────────────────────────────────────────────────
class TetrisApp:
    def __init__(self, root):
        self.root  = root
        self.game  = Tetris()
        self.keys  = set()

        root.title("TETRIS")
        root.configure(bg=COLORS["bg"])
        root.resizable(False, False)

        # layout: board canvas + sidebar
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg=COLORS["bg"], highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=(18,0), pady=18)

        self.side = tk.Canvas(root, width=SIDEBAR, height=HEIGHT,
                              bg=COLORS["panel"], highlightthickness=0)
        self.side.grid(row=0, column=1, padx=(8,18), pady=18)

        root.bind("<KeyPress>",   self._key_down)
        root.bind("<KeyRelease>", self._key_up)

        self._last_tick = 0
        self._last_das  = 0
        self._das_active= False

        self._schedule_gravity()
        self._loop()

    # ── input ─────────────────────────────────────────────────────────────────
    def _key_down(self, e):
        k = e.keysym
        if k == "p" or k == "P":
            self.game.paused = not self.game.paused
            return
        if k == "r" or k == "R":
            self.game.reset()
            self._schedule_gravity()
            return
        if self.game.over or self.game.paused:
            return
        if k in ("Left","Right","Down","Up","space","z","x","Z","X","c","C"):
            if k not in self.keys:
                self.keys.add(k)
                self._handle_key(k)
                self._das_start = self.root.after(170, self._das_repeat, k)

    def _key_up(self, e):
        k = e.keysym
        self.keys.discard(k)

    def _handle_key(self, k):
        g = self.game
        if   k == "Left":  g.move(-1)
        elif k == "Right": g.move(1)
        elif k == "Down":  g.soft_drop()
        elif k in ("Up","x","X"): g.rotate(1)
        elif k in ("z","Z"):      g.rotate(-1)
        elif k == "space": g.hard_drop()

    def _das_repeat(self, k):
        if k in self.keys and not self.game.over and not self.game.paused:
            if k in ("Left","Right","Down"):
                self._handle_key(k)
            self.root.after(50, self._das_repeat, k)

    # ── gravity loop ──────────────────────────────────────────────────────────
    def _schedule_gravity(self):
        if hasattr(self, "_grav_id"):
            self.root.after_cancel(self._grav_id)
        self._grav_id = self.root.after(self.game.tick_speed(), self._gravity_tick)

    def _gravity_tick(self):
        g = self.game
        if not g.over and not g.paused:
            moved = g.gravity()
            if not moved:
                # piece is grounded — lock immediately
                g._lock()
            self._schedule_gravity()
        else:
            self._grav_id = self.root.after(200, self._gravity_tick)

    # ── render loop ───────────────────────────────────────────────────────────
    def _loop(self):
        self._draw()
        self.root.after(1000 // FPS, self._loop)

    def _draw(self):
        c  = self.canvas
        g  = self.game
        c.delete("all")

        # grid lines
        for col in range(COLS + 1):
            x = col * CELL
            c.create_line(x, 0, x, HEIGHT, fill=COLORS["grid"], width=1)
        for row in range(ROWS + 1):
            y = row * CELL
            c.create_line(0, y, WIDTH, y, fill=COLORS["grid"], width=1)

        # board cells
        for r in range(ROWS):
            for col in range(COLS):
                if g.board[r][col]:
                    self._draw_cell(c, col, r, COLORS[g.board[r][col]])

        if not g.over:
            # ghost
            gy = g.ghost_y()
            for cx, cy in piece_cells(g.shape, g.rot, g.x, gy):
                if cy >= 0:
                    self._draw_cell(c, cx, cy, COLORS["ghost"], ghost=True)
            # active piece
            for cx, cy in piece_cells(g.shape, g.rot, g.x, g.y):
                if cy >= 0:
                    self._draw_cell(c, cx, cy, COLORS[g.shape])

        # overlay messages
        if g.over:
            self._overlay(c, "GAME OVER", "R to restart")
        elif g.paused:
            self._overlay(c, "PAUSED", "P to resume")

        # sidebar
        self._draw_sidebar()

    def _draw_cell(self, canvas, col, row, color, ghost=False):
        x1, y1 = col*CELL+1, row*CELL+1
        x2, y2 = x1+CELL-2,  y1+CELL-2
        if ghost:
            canvas.create_rectangle(x1, y1, x2, y2,
                                     outline=color, fill="", width=1,
                                     stipple="gray25")
        else:
            canvas.create_rectangle(x1, y1, x2, y2,
                                     fill=color, outline="",)
            # inner highlight
            canvas.create_line(x1+2, y1+2, x2-2, y1+2, fill="white", width=1)
            canvas.create_line(x1+2, y1+2, x1+2, y2-2, fill="white", width=1)

    def _overlay(self, canvas, title, sub):
        canvas.create_rectangle(0, HEIGHT//2-60, WIDTH, HEIGHT//2+60,
                                 fill="#000000", stipple="gray50", outline="")
        canvas.create_text(WIDTH//2, HEIGHT//2-18, text=title,
                           fill=COLORS["accent"], font=("Courier", 26, "bold"))
        canvas.create_text(WIDTH//2, HEIGHT//2+18, text=sub,
                           fill=COLORS["text"], font=("Courier", 13))

    def _draw_sidebar(self):
        s  = self.side
        g  = self.game
        s.delete("all")
        pad = 20

        # title
        s.create_text(SIDEBAR//2, 28, text="TETRIS",
                      fill=COLORS["accent"], font=("Courier", 22, "bold"))

        # score / level / lines
        for i, (label, val) in enumerate([
            ("SCORE", g.score),
            ("LEVEL", g.level),
            ("LINES", g.lines),
        ]):
            y = 80 + i * 64
            s.create_text(pad, y,   text=label, anchor="w",
                          fill=COLORS["text"], font=("Courier", 10))
            s.create_text(SIDEBAR-pad, y+20, text=str(val), anchor="e",
                          fill=COLORS["accent"], font=("Courier", 20, "bold"))
            s.create_line(pad, y+34, SIDEBAR-pad, y+34,
                          fill=COLORS["grid"], width=1)

        # next piece preview
        ny = 290
        s.create_text(pad, ny, text="NEXT", anchor="w",
                      fill=COLORS["text"], font=("Courier", 10))
        preview_cells = piece_cells(g.next, 0, 0, 0)
        xs = [p[0] for p in preview_cells]
        ys = [p[1] for p in preview_cells]
        off_x = (SIDEBAR - (max(xs)-min(xs)+1)*CELL) // 2 - min(xs)*CELL
        off_y = ny + 22
        for cx, cy in preview_cells:
            px1 = off_x + cx*CELL + 1
            py1 = off_y + cy*CELL + 1
            px2 = px1 + CELL - 2
            py2 = py1 + CELL - 2
            s.create_rectangle(px1, py1, px2, py2,
                               fill=COLORS[g.next], outline="")
            s.create_line(px1+2, py1+2, px2-2, py1+2, fill="white", width=1)
            s.create_line(px1+2, py1+2, px1+2, py2-2, fill="white", width=1)

        # controls
        controls = [
            ("← →", "Move"),
            ("↑ / X", "Rotate CW"),
            ("Z",    "Rotate CCW"),
            ("↓",    "Soft drop"),
            ("SPC",  "Hard drop"),
            ("P",    "Pause"),
            ("R",    "Restart"),
        ]
        cy_start = HEIGHT - 14 - len(controls) * 20
        for i, (key, action) in enumerate(controls):
            y = cy_start + i * 20
            s.create_text(pad,          y, text=key,    anchor="w",
                          fill=COLORS["accent"], font=("Courier", 9, "bold"))
            s.create_text(SIDEBAR-pad,  y, text=action, anchor="e",
                          fill=COLORS["text"],   font=("Courier", 9))


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = TetrisApp(root)
    root.mainloop()
