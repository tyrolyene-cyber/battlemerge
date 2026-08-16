"use strict";

// --- Constantes de jeu (miroir de main.py) --------------------------------

const GRID_ROWS = 4;
const GRID_COLS = 6;
const BORDER_CARD_COUNT = 3;

const GAUGE_MAX = 100;
const GAUGE_GAIN = 20;
const GAUGE_BONUS_RATIO = 0.5;

// Joueur 1 en bas (row 0), joueur 2 en haut (row GRID_ROWS-1).
const PLAYER_ROWS = { 1: 0, 2: GRID_ROWS - 1 };
const FRONT_ROWS = { 1: 1, 2: GRID_ROWS - 2 };
const PLAYER_SIDE_ROWS = {
  1: new Set([PLAYER_ROWS[1], FRONT_ROWS[1]]),
  2: new Set([PLAYER_ROWS[2], FRONT_ROWS[2]]),
};

const STATE_MENU = "menu";
const STATE_GAME = "game";
const STATE_INDEX = "index";

// --- Etat global ------------------------------------------------------------

let state = STATE_MENU;
let currentPlayer = 1;
let gameOver = false;
let cards = [];
const occupied = new Map();
let selectedCard = null;
let indexBuilt = false;
let cellEls = [];
let turnBannerTimer = null;

// --- Elements DOM -----------------------------------------------------------

const screens = {
  [STATE_MENU]: document.getElementById("screen-menu"),
  [STATE_GAME]: document.getElementById("screen-game"),
  [STATE_INDEX]: document.getElementById("screen-index"),
};

const boardEl = document.getElementById("board");
const labelP1 = document.getElementById("label-p1");
const labelP2 = document.getElementById("label-p2");
const turnBanner = document.getElementById("turn-banner");
const overlayEnd = document.getElementById("overlay-end");
const endTitleEl = document.getElementById("end-title");
const indexGrid = document.getElementById("index-grid");

// --- Helpers data -------------------------------------------------------

function heroKey(tier, number) {
  return `${tier}.${number}`;
}

function heroStats(tier, number) {
  return GAME_DATA.stats[heroKey(tier, number)] || [0, 0];
}

function heroImage(tier, number) {
  return GAME_DATA.cardFiles[heroKey(tier, number)] || null;
}

function fusionKeyFor(a, b) {
  const pair = [a, b].sort((x, y) => x[0] - y[0] || x[1] - y[1]);
  return `${heroKey(pair[0][0], pair[0][1])}+${heroKey(pair[1][0], pair[1][1])}`;
}

function mergeResult(heroA, heroB) {
  const result = GAME_DATA.fusions[fusionKeyFor(heroA, heroB)];
  if (!result) return null;
  if (!GAME_DATA.cardFiles[result]) return null;
  const [tier, number] = result.split(".").map(Number);
  return [tier, number];
}

function tier1Numbers() {
  return Object.keys(GAME_DATA.cardFiles)
    .map((k) => k.split(".").map(Number))
    .filter(([tier]) => tier === 1)
    .map(([, number]) => number);
}

function sampleDistinct(n, k) {
  const pool = Array.from({ length: n }, (_, i) => i);
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, k);
}

// --- Layout du plateau ----------------------------------------------------

function getBoardMetrics() {
  const rect = boardEl.getBoundingClientRect();
  return {
    rect,
    cellW: rect.width / GRID_COLS,
    cellH: rect.height / GRID_ROWS,
  };
}

function cellRect(row, col, metrics) {
  const { cellW, cellH } = metrics;
  return {
    x: col * cellW,
    y: (GRID_ROWS - 1 - row) * cellH,
    w: cellW,
    h: cellH,
  };
}

function pixelToCell(px, py, metrics) {
  const { cellW, cellH } = metrics;
  let col = Math.floor(px / cellW);
  let rowFromTop = Math.floor(py / cellH);
  let row = GRID_ROWS - 1 - rowFromTop;
  col = Math.max(0, Math.min(GRID_COLS - 1, col));
  row = Math.max(0, Math.min(GRID_ROWS - 1, row));
  return { row, col };
}

function renderCells(metrics) {
  boardEl.querySelectorAll(".cell").forEach((el) => el.remove());
  cellEls = [];
  const sideRows = PLAYER_SIDE_ROWS[currentPlayer];
  for (let row = 0; row < GRID_ROWS; row++) {
    for (let col = 0; col < GRID_COLS; col++) {
      const { x, y, w, h } = cellRect(row, col, metrics);
      const el = document.createElement("div");
      el.className = "cell" + (sideRows.has(row) ? " side-active" : "");
      el.style.left = `${x}px`;
      el.style.top = `${y}px`;
      el.style.width = `${w}px`;
      el.style.height = `${h}px`;
      boardEl.appendChild(el);
      cellEls.push({ row, col, el });
    }
  }
}

function updateCellHighlight() {
  const sideRows = PLAYER_SIDE_ROWS[currentPlayer];
  for (const { row, el } of cellEls) {
    el.classList.toggle("side-active", sideRows.has(row));
  }
}

function layoutAll() {
  if (!boardEl.style.backgroundImage) {
    boardEl.style.backgroundImage = `url(${GAME_DATA.background})`;
  }
  const metrics = getBoardMetrics();
  renderCells(metrics);
  for (const card of cards) {
    card.snapToCell(card.row, card.col, metrics);
  }
}

// --- Carte (héros) ----------------------------------------------------------

class Card {
  constructor(row, col, tier, number) {
    this.row = row;
    this.col = col;
    this.tier = tier;
    this.number = number;
    this.x = 0;
    this.y = 0;
    this.w = 0;
    this.h = 0;
    this._dragDX = 0;
    this._dragDY = 0;

    const [hp, atk] = heroStats(tier, number);
    this.baseHp = hp;
    this.baseAtk = atk;
    this.effectiveMaxHp = hp;
    this.hp = hp;
    this.atk = atk;
    this.gauge = 0;

    this.el = document.createElement("div");
    this.el.className = "card";

    const imgPath = heroImage(tier, number);
    if (imgPath) {
      const img = document.createElement("img");
      img.className = "card-img";
      img.src = imgPath;
      img.draggable = false;
      img.alt = heroKey(tier, number);
      this.el.appendChild(img);
    } else {
      const fallback = document.createElement("div");
      fallback.className = "card-fallback";
      fallback.textContent = heroKey(tier, number);
      this.el.appendChild(fallback);
    }

    const badges = document.createElement("div");
    badges.className = "stat-badges";
    this.hpBadge = document.createElement("div");
    this.hpBadge.className = "stat-badge badge-hp";
    this.atkBadge = document.createElement("div");
    this.atkBadge.className = "stat-badge badge-atk";
    badges.append(this.hpBadge, this.atkBadge);
    this.el.appendChild(badges);

    const gaugeTrack = document.createElement("div");
    gaugeTrack.className = "gauge-track";
    this.gaugeFill = document.createElement("div");
    this.gaugeFill.className = "gauge-fill";
    gaugeTrack.appendChild(this.gaugeFill);
    this.el.appendChild(gaugeTrack);

    this.updateHpLabel();
    this.updateAtkLabel();
    this.updateGaugeVisual();

    boardEl.appendChild(this.el);
    this._bindPointerEvents();
  }

  _bindPointerEvents() {
    this.el.addEventListener("pointerdown", (e) => {
      if (state !== STATE_GAME || gameOver) return;
      if (selectedCard !== null) return;
      if (!PLAYER_SIDE_ROWS[currentPlayer].has(this.row)) return;
      e.preventDefault();
      selectedCard = this;
      const metrics = getBoardMetrics();
      const boardX = e.clientX - metrics.rect.left;
      const boardY = e.clientY - metrics.rect.top;
      this._dragDX = boardX - this.x;
      this._dragDY = boardY - this.y;
      this.el.classList.add("dragging");
      this.el.setPointerCapture(e.pointerId);
    });

    this.el.addEventListener("pointermove", (e) => {
      if (selectedCard !== this) return;
      e.preventDefault();
      const metrics = getBoardMetrics();
      const boardX = e.clientX - metrics.rect.left;
      const boardY = e.clientY - metrics.rect.top;
      this.setPositionPx(boardX - this._dragDX, boardY - this._dragDY, this.w, this.h);
    });

    const endDrag = (e) => {
      if (selectedCard !== this) return;
      this.el.classList.remove("dragging");
      finalizeDrop(this);
      selectedCard = null;
    };
    this.el.addEventListener("pointerup", endDrag);
    this.el.addEventListener("pointercancel", endDrag);
  }

  setPositionPx(x, y, w, h) {
    this.x = x;
    this.y = y;
    this.w = w;
    this.h = h;
    this.el.style.left = `${x}px`;
    this.el.style.top = `${y}px`;
    this.el.style.width = `${w}px`;
    this.el.style.height = `${h}px`;
  }

  snapToCell(row, col, metrics) {
    this.row = row;
    this.col = col;
    const { x, y, w, h } = cellRect(row, col, metrics);
    const margin = Math.max(3, Math.min(w, h) * 0.07);
    this.setPositionPx(x + margin, y + margin, w - 2 * margin, h - 2 * margin);
  }

  updateHpLabel() {
    this.hpBadge.textContent = Math.max(this.hp, 0);
  }

  updateAtkLabel() {
    this.atkBadge.textContent = this.atk;
  }

  updateGaugeVisual() {
    this.gaugeFill.style.width = `${(this.gauge / GAUGE_MAX) * 100}%`;
    this.el.classList.toggle("card-charged", this.isCharged());
  }

  recomputeStats() {
    const ratio = GAUGE_BONUS_RATIO * (this.gauge / GAUGE_MAX);
    const newMaxHp = Math.round(this.baseHp * (1 + ratio));
    this.hp += newMaxHp - this.effectiveMaxHp;
    this.effectiveMaxHp = newMaxHp;
    this.atk = Math.round(this.baseAtk * (1 + ratio));
    this.updateHpLabel();
    this.updateAtkLabel();
  }

  addGauge(amount) {
    if (this.gauge >= GAUGE_MAX) return;
    this.gauge = Math.min(GAUGE_MAX, this.gauge + amount);
    this.recomputeStats();
    this.updateGaugeVisual();
  }

  isCharged() {
    return this.gauge >= GAUGE_MAX;
  }

  destroy() {
    this.el.remove();
  }
}

// --- Logique de partie -------------------------------------------------

function occupiedKey(row, col) {
  return `${row},${col}`;
}

function removeFromCardsArray(card) {
  const idx = cards.indexOf(card);
  if (idx >= 0) cards.splice(idx, 1);
}

function spawnInitialCards() {
  const t1 = tier1Numbers();
  if (t1.length === 0) return;
  for (const player of [1, 2]) {
    const row = PLAYER_ROWS[player];
    const cols = sampleDistinct(GRID_COLS, Math.min(BORDER_CARD_COUNT, GRID_COLS));
    for (const col of cols) {
      const number = t1[Math.floor(Math.random() * t1.length)];
      const card = new Card(row, col, 1, number);
      cards.push(card);
      occupied.set(occupiedKey(row, col), card);
    }
  }
}

function clearBoard() {
  for (const card of cards) card.destroy();
  cards.length = 0;
  occupied.clear();
}

function finalizeDrop(card) {
  const metrics = getBoardMetrics();

  if (gameOver) {
    card.snapToCell(card.row, card.col, metrics);
    return;
  }

  const centerX = card.x + card.w / 2;
  const centerY = card.y + card.h / 2;
  const { row, col } = pixelToCell(centerX, centerY, metrics);
  const oldRow = card.row;
  const oldCol = card.col;
  const sideRows = PLAYER_SIDE_ROWS[currentPlayer];

  if (!sideRows.has(row)) {
    card.snapToCell(oldRow, oldCol, metrics);
    return;
  }

  const targetKey = occupiedKey(row, col);
  const target = occupied.get(targetKey);
  let turnUsed = false;

  if (!target || target === card) {
    if (row !== oldRow || col !== oldCol) {
      occupied.delete(occupiedKey(oldRow, oldCol));
      card.snapToCell(row, col, metrics);
      occupied.set(targetKey, card);
      turnUsed = true;
    } else {
      card.snapToCell(oldRow, oldCol, metrics);
    }
  } else {
    const result = mergeResult([card.tier, card.number], [target.tier, target.number]);
    if (result && card.isCharged() && target.isCharged()) {
      occupied.delete(occupiedKey(oldRow, oldCol));
      occupied.delete(targetKey);
      removeFromCardsArray(card);
      removeFromCardsArray(target);
      card.destroy();
      target.destroy();
      const merged = new Card(row, col, result[0], result[1]);
      merged.snapToCell(row, col, metrics);
      cards.push(merged);
      occupied.set(targetKey, merged);
      turnUsed = true;
    } else {
      card.snapToCell(oldRow, oldCol, metrics);
    }
  }

  if (turnUsed) {
    advanceTurn();
  }
}

function removeDeadHero(card) {
  occupied.delete(occupiedKey(card.row, card.col));
  removeFromCardsArray(card);
  card.destroy();
}

function resolveCombat() {
  const row1 = FRONT_ROWS[1];
  const row2 = FRONT_ROWS[2];

  const p1Heroes = cards.filter((c) => c.row === row1).sort((a, b) => b.col - a.col);
  const p2Heroes = cards.filter((c) => c.row === row2).sort((a, b) => b.col - a.col);

  const aliveP1 = new Set(p1Heroes);
  const aliveP2 = new Set(p2Heroes);

  let i = 0;
  let j = 0;
  let attackerIsP1 = true;

  while (i < p1Heroes.length || j < p2Heroes.length) {
    if (attackerIsP1) {
      if (i < p1Heroes.length) {
        const attacker = p1Heroes[i];
        i += 1;
        if (aliveP1.has(attacker) && aliveP2.size > 0) {
          const targets = Array.from(aliveP2);
          const target = targets[Math.floor(Math.random() * targets.length)];
          target.hp -= attacker.atk;
          attacker.addGauge(GAUGE_GAIN);
          target.addGauge(GAUGE_GAIN);
          target.updateHpLabel();
          if (target.hp <= 0) aliveP2.delete(target);
        }
      }
    } else if (j < p2Heroes.length) {
      const attacker = p2Heroes[j];
      j += 1;
      if (aliveP2.has(attacker) && aliveP1.size > 0) {
        const targets = Array.from(aliveP1);
        const target = targets[Math.floor(Math.random() * targets.length)];
        target.hp -= attacker.atk;
        attacker.addGauge(GAUGE_GAIN);
        target.addGauge(GAUGE_GAIN);
        target.updateHpLabel();
        if (target.hp <= 0) aliveP1.delete(target);
      }
    }
    attackerIsP1 = !attackerIsP1;
  }

  for (const hero of p1Heroes) if (!aliveP1.has(hero)) removeDeadHero(hero);
  for (const hero of p2Heroes) if (!aliveP2.has(hero)) removeDeadHero(hero);
}

function countCardsForPlayer(player) {
  const rows = PLAYER_SIDE_ROWS[player];
  return cards.filter((c) => rows.has(c.row)).length;
}

function checkGameOver() {
  const p1Count = countCardsForPlayer(1);
  const p2Count = countCardsForPlayer(2);
  if (p1Count > 0 && p2Count > 0) return;

  gameOver = true;
  let title;
  if (p1Count === 0 && p2Count === 0) title = "Égalité !";
  else if (p1Count === 0) title = "Joueur 2 gagne !";
  else title = "Joueur 1 gagne !";
  showEndOverlay(title);
}

function advanceTurn() {
  const roundComplete = currentPlayer === 2;
  currentPlayer = currentPlayer === 1 ? 2 : 1;
  if (roundComplete) {
    resolveCombat();
  }
  updatePlayerLabels();
  updateCellHighlight();
  if (roundComplete) {
    checkGameOver();
  }
  if (!gameOver) {
    showTurnBanner(`Au tour de Joueur ${currentPlayer}`);
  }
}

function passTurn() {
  if (state !== STATE_GAME || gameOver) return;
  advanceTurn();
}

function updatePlayerLabels() {
  labelP1.classList.toggle("active", currentPlayer === 1);
  labelP2.classList.toggle("active", currentPlayer === 2);
}

function showTurnBanner(text) {
  turnBanner.textContent = text;
  turnBanner.classList.add("show");
  clearTimeout(turnBannerTimer);
  turnBannerTimer = setTimeout(() => turnBanner.classList.remove("show"), 900);
}

function showEndOverlay(title) {
  endTitleEl.textContent = title;
  overlayEnd.classList.remove("hidden");
}

function hideEndOverlay() {
  overlayEnd.classList.add("hidden");
}

function startNewGame() {
  clearBoard();
  spawnInitialCards();
  currentPlayer = 1;
  gameOver = false;
  hideEndOverlay();
  updatePlayerLabels();
  layoutAll();
}

// --- Index des héros ---------------------------------------------------

function buildHeroIndex() {
  if (indexBuilt) return;
  indexBuilt = true;

  const heroes = Object.keys(GAME_DATA.cardFiles)
    .map((k) => k.split(".").map(Number))
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  if (heroes.length === 0) {
    indexGrid.textContent = "Aucun héros trouvé dans assets/cards/.";
    return;
  }

  for (const [tier, number] of heroes) {
    const key = heroKey(tier, number);
    const [hp, atk] = GAME_DATA.stats[key] || [0, 0];

    const item = document.createElement("div");
    item.className = "index-item";

    const img = document.createElement("img");
    img.src = GAME_DATA.cardFiles[key];
    img.alt = key;
    img.loading = "lazy";

    const label = document.createElement("div");
    label.className = "index-label";
    label.textContent = key;

    const stats = document.createElement("div");
    stats.className = "index-stats";
    stats.innerHTML = `<span class="hp">♥ ${hp}</span><span class="atk">⚔ ${atk}</span>`;

    item.append(img, label, stats);
    indexGrid.appendChild(item);
  }
}

// --- Navigation entre écrans ---------------------------------------------

function switchState(next) {
  state = next;
  for (const [key, el] of Object.entries(screens)) {
    el.classList.toggle("active", key === next);
  }
  if (next === STATE_GAME) {
    layoutAll();
  }
}

// --- Liaison des évènements -----------------------------------------------

document.getElementById("btn-play").addEventListener("click", () => {
  switchState(STATE_GAME);
  startNewGame();
});

document.getElementById("btn-index").addEventListener("click", () => {
  buildHeroIndex();
  switchState(STATE_INDEX);
});

document.getElementById("btn-index-back").addEventListener("click", () => {
  switchState(STATE_MENU);
});

document.getElementById("btn-menu").addEventListener("click", () => {
  switchState(STATE_MENU);
});

document.getElementById("btn-pass").addEventListener("click", passTurn);

document.getElementById("btn-restart").addEventListener("click", () => {
  hideEndOverlay();
  startNewGame();
});

document.getElementById("btn-end-menu").addEventListener("click", () => {
  hideEndOverlay();
  switchState(STATE_MENU);
});

let resizeTimer = null;
function onViewportChange() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state === STATE_GAME) layoutAll();
  }, 80);
}
window.addEventListener("resize", onViewportChange);
window.addEventListener("orientationchange", onViewportChange);

// Enregistrement du service worker (PWA installable sur iPhone).
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
