const COLS = 10;
const ROWS = 20;
const CELL = 34;

const COLORS = {
    "I": "#00ECFF",
    "O": "#FFE600",
    "T": "#CC44FF",
    "S": "#44FF77",
    "Z": "#FF4455",
    "J": "#4477FF",
    "L": "#FF9900",
    "ghost": "#FFFFFF",
    "bg": "#0D0D14",
    "grid": "#1A1A2E",
};

let canvas = document.getElementById('gameCanvas');
let ctx = canvas.getContext('2d');
let nextCanvas = document.getElementById('nextCanvas');
let nextCtx = nextCanvas.getContext('2d');

let socket = io({
    transports: ['polling']
});
let gameState = null;
let keys = {};
let gravityInterval = null;

// ── Rendering ────────────────────────────────────────────────────────────────

function drawCell(context, col, row, color, ghost = false) {
    const x1 = col * CELL + 1;
    const y1 = row * CELL + 1;
    const x2 = x1 + CELL - 2;
    const y2 = y1 + CELL - 2;

    if (ghost) {
        context.strokeStyle = color;
        context.lineWidth = 1;
        context.setLineDash([2, 2]);
        context.strokeRect(x1, y1, CELL - 2, CELL - 2);
        context.setLineDash([]);
    } else {
        context.fillStyle = color;
        context.fillRect(x1, y1, CELL - 2, CELL - 2);
        // inner highlight
        context.strokeStyle = "white";
        context.lineWidth = 1;
        context.strokeRect(x1 + 2, y1 + 2, CELL - 6, CELL - 6);
    }
}

function drawBoard() {
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // grid lines
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;
    for (let col = 0; col <= COLS; col++) {
        ctx.beginPath();
        ctx.moveTo(col * CELL, 0);
        ctx.lineTo(col * CELL, ROWS * CELL);
        ctx.stroke();
    }
    for (let row = 0; row <= ROWS; row++) {
        ctx.beginPath();
        ctx.moveTo(0, row * CELL);
        ctx.lineTo(COLS * CELL, row * CELL);
        ctx.stroke();
    }

    // board cells
    if (gameState && gameState.board) {
        for (let r = 0; r < ROWS; r++) {
            for (let col = 0; col < COLS; col++) {
                if (gameState.board[r][col]) {
                    drawCell(ctx, col, r, COLORS[gameState.board[r][col]]);
                }
            }
        }
    }

    // ghost and active piece
    if (gameState && !gameState.over) {
        const pieceCells = getPieceCells(gameState.shape, gameState.rot, gameState.x, gameState.ghost_y);
        for (let [cx, cy] of pieceCells) {
            if (cy >= 0) {
                drawCell(ctx, cx, cy, COLORS.ghost, true);
            }
        }

        const activeCells = getPieceCells(gameState.shape, gameState.rot, gameState.x, gameState.y);
        for (let [cx, cy] of activeCells) {
            if (cy >= 0) {
                drawCell(ctx, cx, cy, COLORS[gameState.shape]);
            }
        }
    }

    // overlay messages
    if (gameState) {
        if (gameState.over) {
            drawOverlay("GAME OVER", "R to restart");
        } else if (gameState.paused) {
            drawOverlay("PAUSED", "P to resume");
        }
    }
}

function drawOverlay(title, sub) {
    ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(0, ROWS * CELL / 2 - 60, COLS * CELL, 120);
    
    ctx.fillStyle = "#00ECFF";
    ctx.font = "bold 26px Courier";
    ctx.textAlign = "center";
    ctx.fillText(title, COLS * CELL / 2, ROWS * CELL / 2 - 18);

    ctx.fillStyle = "#E0E0FF";
    ctx.font = "13px Courier";
    ctx.fillText(sub, COLS * CELL / 2, ROWS * CELL / 2 + 18);
}

function drawNextPiece() {
    nextCtx.fillStyle = COLORS.bg;
    nextCtx.fillRect(0, 0, nextCanvas.width, nextCanvas.height);

    if (gameState && gameState.next) {
        const pieceCells = getPieceCells(gameState.next, 0, 0, 0);
        const xs = pieceCells.map(p => p[0]);
        const ys = pieceCells.map(p => p[1]);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const width = (maxX - minX + 1) * CELL;
        const height = (maxY - minY + 1) * CELL;
        const offsetX = (nextCanvas.width - width) / 2 - minX * CELL;
        const offsetY = (nextCanvas.height - height) / 2 - minY * CELL;

        for (let [cx, cy] of pieceCells) {
            const x = offsetX + cx * CELL + 1;
            const y = offsetY + cy * CELL + 1;
            nextCtx.fillStyle = COLORS[gameState.next];
            nextCtx.fillRect(x, y, CELL - 2, CELL - 2);
            nextCtx.strokeStyle = "white";
            nextCtx.lineWidth = 1;
            nextCtx.strokeRect(x + 2, y + 2, CELL - 6, CELL - 6);
        }
    }
}

function updateUI() {
    if (gameState) {
        document.getElementById('score').textContent = gameState.score;
        document.getElementById('level').textContent = gameState.level;
        document.getElementById('lines').textContent = gameState.lines;
    }
}

function getPieceCells(shape, rot, x, y) {
    const TETROMINOES = {
        "I": [[[0,1],[1,1],[2,1],[3,1]], [[2,0],[2,1],[2,2],[2,3]], [[0,2],[1,2],[2,2],[3,2]], [[1,0],[1,1],[1,2],[1,3]]],
        "O": [[[1,0],[2,0],[1,1],[2,1]], [[1,0],[2,0],[1,1],[2,1]], [[1,0],[2,0],[1,1],[2,1]], [[1,0],[2,0],[1,1],[2,1]]],
        "T": [[[0,1],[1,1],[2,1],[1,0]], [[1,0],[1,1],[1,2],[2,1]], [[0,1],[1,1],[2,1],[1,2]], [[1,0],[1,1],[1,2],[0,1]]],
        "S": [[[1,0],[2,0],[0,1],[1,1]], [[1,0],[1,1],[2,1],[2,2]], [[1,1],[2,1],[0,2],[1,2]], [[0,0],[0,1],[1,1],[1,2]]],
        "Z": [[[0,0],[1,0],[1,1],[2,1]], [[2,0],[1,1],[2,1],[1,2]], [[0,1],[1,1],[1,2],[2,2]], [[1,0],[0,1],[1,1],[0,2]]],
        "J": [[[0,0],[0,1],[1,1],[2,1]], [[1,0],[2,0],[1,1],[1,2]], [[0,1],[1,1],[2,1],[2,2]], [[1,0],[1,1],[0,2],[1,2]]],
        "L": [[[2,0],[0,1],[1,1],[2,1]], [[1,0],[1,1],[1,2],[2,2]], [[0,1],[1,1],[2,1],[0,2]], [[0,0],[1,0],[1,1],[1,2]]],
    };
    const cells = TETROMINOES[shape][rot % TETROMINOES[shape].length];
    return cells.map(([dx, dy]) => [x + dx, y + dy]);
}

// ── Input ────────────────────────────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    if (keys[k]) return;
    keys[k] = true;
    handleKey(k, true);
});

document.addEventListener('keyup', (e) => {
    const k = e.key.toLowerCase();
    keys[k] = false;
});

function handleKey(k, isDown) {
    if (!isDown) return;

    if (k === 'p') {
        socket.emit('pause');
        return;
    }
    if (k === 'r') {
        socket.emit('reset');
        return;
    }
    if (gameState && (gameState.over || gameState.paused)) return;

    if (k === 'arrowleft') socket.emit('move', { direction: 'left' });
    else if (k === 'arrowright') socket.emit('move', { direction: 'right' });
    else if (k === 'arrowdown') socket.emit('move', { direction: 'down' });
    else if (k === 'arrowup' || k === 'x') socket.emit('rotate', { direction: 1 });
    else if (k === 'z') socket.emit('rotate', { direction: -1 });
    else if (k === ' ') {
        socket.emit('hard_drop');
    }
}

// ── WebSocket Events ────────────────────────────────────────────────────────

socket.on('state', (state) => {
    gameState = state;
    drawBoard();
    drawNextPiece();
    updateUI();
});

socket.on('connect', () => {
    console.log('Connected to server');
    // Start gravity timer
    if (gravityInterval) clearInterval(gravityInterval);
    gravityInterval = setInterval(() => {
        socket.emit('gravity');
    }, 100);
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    if (gravityInterval) clearInterval(gravityInterval);
});

// ── Animation Loop ──────────────────────────────────────────────────────────

function animate() {
    drawBoard();
    drawNextPiece();
    requestAnimationFrame(animate);
}

animate();
