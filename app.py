#!/usr/bin/env python3
"""
Tetris Web App — Flask + WebSocket backend
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tetris-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── constants ──────────────────────────────────────────────────────────────────
COLS, ROWS = 10, 20
LEVEL_SPEEDS = [4000,3500,3000,2500,2000,1600,1250,950,700,500,400,300,250,200,150]
POINTS = [0, 100, 300, 500, 800]

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

# ── game state per connection ──────────────────────────────────────────────────
games = {}

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
            return True
        return False

    def rotate(self, d=1):
        new_rot = (self.rot + d) % len(TETROMINOES[self.shape])
        for kick in [0, 1, -1, 2, -2]:
            if self._valid(self.x + kick, self.y, new_rot):
                self.x   += kick
                self.rot  = new_rot
                return True
        return False

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
        if not self._valid(self.x, self.y + 1, self.rot):
            return False
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

    def get_state(self):
        """Return game state as JSON-serializable dict."""
        return {
            'board': self.board,
            'score': self.score,
            'lines': self.lines,
            'level': self.level,
            'over': self.over,
            'paused': self.paused,
            'shape': self.shape,
            'next': self.next,
            'rot': self.rot,
            'x': self.x,
            'y': self.y,
            'ghost_y': self.ghost_y(),
        }


# ── routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── websocket events ──────────────────────────────────────────────────────────
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    games[sid] = Tetris()
    emit('state', games[sid].get_state())


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in games:
        del games[sid]


@socketio.on('move')
def handle_move(data):
    sid = request.sid
    if sid not in games:
        return
    g = games[sid]
    if g.over or g.paused:
        return
    direction = data.get('direction')
    if direction == 'left':
        g.move(-1)
    elif direction == 'right':
        g.move(1)
    elif direction == 'down':
        g.soft_drop()
    emit('state', g.get_state(), to=sid)


@socketio.on('rotate')
def handle_rotate(data):
    sid = request.sid
    if sid not in games:
        return
    g = games[sid]
    if g.over or g.paused:
        return
    direction = data.get('direction', 1)
    g.rotate(direction)
    emit('state', g.get_state(), to=sid)


@socketio.on('hard_drop')
def handle_hard_drop():
    sid = request.sid
    if sid not in games:
        return
    g = games[sid]
    if g.over or g.paused:
        return
    g.hard_drop()
    emit('state', g.get_state(), to=sid)


@socketio.on('gravity')
def handle_gravity():
    sid = request.sid
    if sid not in games:
        return
    g = games[sid]
    if not g.over and not g.paused:
        moved = g.gravity()
        if not moved:
            g._lock()
    emit('state', g.get_state(), to=sid)


@socketio.on('pause')
def handle_pause():
    sid = request.sid
    if sid not in games:
        return
    g = games[sid]
    g.paused = not g.paused
    emit('state', g.get_state(), to=sid)


@socketio.on('reset')
def handle_reset():
    sid = request.sid
    if sid not in games:
        return
    games[sid] = Tetris()
    emit('state', games[sid].get_state(), to=sid)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='localhost', port=5000)
