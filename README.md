# Tetris Web App

A web-based Tetris game built with Flask and WebSockets, playable in any browser at localhost.

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python app.py
   ```

3. **Open in browser:**
   Navigate to `http://localhost:5000` in your web browser.

## Controls

| Key | Action |
|-----|--------|
| ← → | Move left/right |
| ↑ or X | Rotate clockwise |
| Z | Rotate counter-clockwise |
| ↓ | Soft drop |
| Space | Hard drop |
| P | Pause/Resume |
| R | Restart game |

## Features

- Real-time game state synchronization via WebSocket
- Ghost piece preview
- Next piece preview
- Score, level, and lines tracking
- Responsive design for desktop and tablets
- Pure Python game logic on the backend
- HTML5 Canvas rendering on the frontend

## Architecture

- **Backend:** Flask + Flask-SocketIO (Python)
- **Frontend:** HTML5 Canvas + Vanilla JavaScript
- **Communication:** WebSocket (Socket.IO)

The game logic runs on the server and communicates game state to connected clients via WebSocket, ensuring consistency and preventing cheating.
