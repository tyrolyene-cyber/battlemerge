import random
import re
from pathlib import Path

import pyglet
from pyglet import shapes
from pyglet.window import mouse

from fusions import FUSIONS
from stats import STATS

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
GRID_ROWS = 4
GRID_COLS = 6
MARGIN = 40
CARD_MARGIN = 8
BORDER_CARD_COUNT = 3
STAT_BADGE_HEIGHT = 18
STAT_BADGE_GAP = 4

# Jauge de charge : se remplit quand un heros attaque ou prend des degats.
# Plus elle est haute, plus ses stats augmentent ; pleine, il peut fusionner.
GAUGE_HEIGHT = 6
GAUGE_MAX = 100
GAUGE_GAIN = 20
GAUGE_BONUS_RATIO = 0.5  # +50% de stats a jauge pleine

# Ligne du bord (spawn) de chaque joueur : joueur 1 en bas, joueur 2 en haut.
PLAYER_ROWS = {1: 0, 2: GRID_ROWS - 1}
# Ligne de devant (front line) de chaque joueur, au milieu du plateau.
FRONT_ROWS = {1: 1, 2: GRID_ROWS - 2}
# Toutes les lignes qu'un joueur peut jouer sur son tour (son cote).
PLAYER_SIDE_ROWS = {
    player: {PLAYER_ROWS[player], FRONT_ROWS[player]} for player in (1, 2)
}

ASSETS_DIR = Path(__file__).parent / "assets"
BACKGROUND_PATH = ASSETS_DIR / "background.png"
CARDS_DIR = ASSETS_DIR / "cards"

# Nom de fichier attendu pour chaque carte : "<tier>.<numero>.png"
# (ex: 1.1.png, 1.2.png, 2.1.png). Le premier nombre est le tier, le
# second le numero du heros dans ce tier.
CARD_FILENAME_RE = re.compile(r"^(\d+)\.(\d+)$")

window = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption="BattleMerge")
pyglet.gl.glClearColor(0.09, 0.1, 0.13, 1)

batch = pyglet.graphics.Batch()
background_group = pyglet.graphics.Group(order=-1)
cell_group = pyglet.graphics.Group(order=0)
card_group = pyglet.graphics.Group(order=1)
badge_shape_group = pyglet.graphics.Group(order=2)
label_group = pyglet.graphics.Group(order=3)

board_width = WINDOW_WIDTH - 2 * MARGIN
board_height = WINDOW_HEIGHT - 2 * MARGIN
cell_width = board_width / GRID_COLS
cell_height = board_height / GRID_ROWS


def cell_rect(row, col):
    x = MARGIN + col * cell_width
    y = MARGIN + row * cell_height
    return x, y, cell_width, cell_height


def pixel_to_cell(px, py):
    col = int((px - MARGIN) // cell_width)
    row = int((py - MARGIN) // cell_height)
    col = max(0, min(GRID_COLS - 1, col))
    row = max(0, min(GRID_ROWS - 1, row))
    return row, col


# --- Background -------------------------------------------------------

background_sprite = None
if BACKGROUND_PATH.exists():
    bg_image = pyglet.image.load(str(BACKGROUND_PATH))
    background_sprite = pyglet.sprite.Sprite(
        bg_image, x=0, y=0, batch=batch, group=background_group
    )
    background_sprite.scale_x = WINDOW_WIDTH / bg_image.width
    background_sprite.scale_y = WINDOW_HEIGHT / bg_image.height


# --- Card catalog --------------------------------------------------------
# Seuls les heros dont l'image existe dans assets/cards/ peuvent
# apparaitre dans le jeu.

CARD_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")


def scan_card_catalog():
    catalog = {}
    if CARDS_DIR.exists():
        for path in CARDS_DIR.iterdir():
            if path.suffix.lower() not in CARD_IMAGE_EXTENSIONS:
                continue
            match = CARD_FILENAME_RE.match(path.stem)
            if not match:
                continue
            tier, number = int(match.group(1)), int(match.group(2))
            catalog.setdefault(tier, {})[number] = path
    return catalog


CARD_CATALOG = scan_card_catalog()

_card_image_cache = {}


def get_card_image(tier, number):
    key = (tier, number)
    if key in _card_image_cache:
        return _card_image_cache[key]
    path = CARD_CATALOG.get(tier, {}).get(number)
    image = pyglet.image.load(str(path)) if path else None
    _card_image_cache[key] = image
    return image


def merge_result(hero_a, hero_b):
    """hero_* = (tier, numero). Retourne (tier, numero) resultat ou None."""
    key = tuple(sorted((hero_a, hero_b)))
    result = FUSIONS.get(key)
    if result is None:
        return None
    result_tier, result_number = result
    if result_number not in CARD_CATALOG.get(result_tier, {}):
        return None
    return result


cells = []
if background_sprite is None:
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x, y, w, h = cell_rect(row, col)
            cells.append(
                shapes.BorderedRectangle(
                    x, y, w, h,
                    border=2,
                    color=(35, 38, 48),
                    border_color=(90, 95, 115),
                    batch=batch,
                    group=cell_group,
                )
            )


class Card:
    def __init__(self, row, col, tier, number):
        self.row = row
        self.col = col
        self.tier = tier
        self.number = number
        x, y, w, h = cell_rect(row, col)
        self.width = w - 2 * CARD_MARGIN
        self.height = h - 2 * CARD_MARGIN
        self.x = x + CARD_MARGIN
        self.y = y + CARD_MARGIN

        image = get_card_image(tier, number)
        self.sprite = None
        self.rect = None
        self.label = None

        if image is not None:
            self.sprite = pyglet.sprite.Sprite(
                image, x=self.x, y=self.y, batch=batch, group=card_group
            )
            self.sprite.scale_x = self.width / image.width
            self.sprite.scale_y = self.height / image.height
        else:
            # Secours si l'image attendue est introuvable au chargement.
            self.rect = shapes.BorderedRectangle(
                self.x, self.y, self.width, self.height,
                border=3,
                color=(120, 40, 40),
                border_color=(255, 255, 255),
                batch=batch,
                group=card_group,
            )
            self.label = pyglet.text.Label(
                f"{tier}.{number}",
                font_size=18,
                weight="bold",
                x=self.x + self.width / 2,
                y=self.y + self.height / 2,
                anchor_x="center",
                anchor_y="center",
                color=(255, 255, 255, 255),
                batch=batch,
                group=label_group,
            )

        # Stats de base (fixes) et jauge de charge (0 a GAUGE_MAX).
        self.base_hp, self.base_atk = STATS.get((tier, number), (0, 0))
        self.effective_max_hp = self.base_hp
        self.hp = self.base_hp
        self.atk = self.base_atk
        self.gauge = 0

        # Jauge de charge, tout en bas du personnage.
        self.gauge_bg = shapes.BorderedRectangle(
            self.x, self.y, self.width, GAUGE_HEIGHT,
            border=1,
            color=(25, 25, 30),
            border_color=(90, 90, 100),
            batch=batch,
            group=badge_shape_group,
        )
        self.gauge_fill = shapes.Rectangle(
            self.x, self.y, 0, GAUGE_HEIGHT,
            color=(90, 170, 255),
            batch=batch,
            group=badge_shape_group,
        )

        # Cadres de statistiques : vie (rouge) et attaque (jaune), juste
        # au-dessus de la jauge de charge.
        badge_width = self.width / 2 - STAT_BADGE_GAP / 2
        badge_x = self.x
        badge_y = self.y + GAUGE_HEIGHT

        self.hp_badge = shapes.BorderedRectangle(
            badge_x, badge_y, badge_width, STAT_BADGE_HEIGHT,
            border=2,
            color=(60, 10, 10),
            border_color=(220, 40, 40),
            batch=batch,
            group=badge_shape_group,
        )
        self.hp_label = pyglet.text.Label(
            str(self.hp),
            font_size=11,
            weight="bold",
            x=badge_x + badge_width / 2,
            y=badge_y + STAT_BADGE_HEIGHT / 2,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
            batch=batch,
            group=label_group,
        )

        atk_x = self.x + self.width - badge_width
        self.atk_badge = shapes.BorderedRectangle(
            atk_x, badge_y, badge_width, STAT_BADGE_HEIGHT,
            border=2,
            color=(60, 55, 5),
            border_color=(230, 200, 30),
            batch=batch,
            group=badge_shape_group,
        )
        self.atk_label = pyglet.text.Label(
            str(self.atk),
            font_size=11,
            weight="bold",
            x=atk_x + badge_width / 2,
            y=badge_y + STAT_BADGE_HEIGHT / 2,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
            batch=batch,
            group=label_group,
        )

    def set_position_px(self, x, y):
        self.x = x
        self.y = y
        if self.sprite is not None:
            self.sprite.x = x
            self.sprite.y = y
        if self.rect is not None:
            self.rect.x = x
            self.rect.y = y
        if self.label is not None:
            self.label.x = x + self.width / 2
            self.label.y = y + self.height / 2

        self.gauge_bg.x = x
        self.gauge_bg.y = y
        self.gauge_fill.x = x
        self.gauge_fill.y = y

        badge_width = self.width / 2 - STAT_BADGE_GAP / 2
        badge_y = y + GAUGE_HEIGHT
        self.hp_badge.x = x
        self.hp_badge.y = badge_y
        self.hp_label.x = x + badge_width / 2
        self.hp_label.y = badge_y + STAT_BADGE_HEIGHT / 2

        atk_x = x + self.width - badge_width
        self.atk_badge.x = atk_x
        self.atk_badge.y = badge_y
        self.atk_label.x = atk_x + badge_width / 2
        self.atk_label.y = badge_y + STAT_BADGE_HEIGHT / 2

    def snap_to_cell(self, row, col):
        self.row = row
        self.col = col
        cx, cy, w, h = cell_rect(row, col)
        self.set_position_px(cx + CARD_MARGIN, cy + CARD_MARGIN)

    def contains_point(self, px, py):
        return (
            self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height
        )

    def update_hp_label(self):
        self.hp_label.text = str(max(self.hp, 0))

    def update_atk_label(self):
        self.atk_label.text = str(self.atk)

    def update_gauge_visual(self):
        self.gauge_fill.width = self.width * (self.gauge / GAUGE_MAX)

    def recompute_stats(self):
        ratio = GAUGE_BONUS_RATIO * (self.gauge / GAUGE_MAX)
        new_max_hp = round(self.base_hp * (1 + ratio))
        self.hp += new_max_hp - self.effective_max_hp
        self.effective_max_hp = new_max_hp
        self.atk = round(self.base_atk * (1 + ratio))
        self.update_hp_label()
        self.update_atk_label()

    def add_gauge(self, amount):
        if self.gauge >= GAUGE_MAX:
            return
        self.gauge = min(GAUGE_MAX, self.gauge + amount)
        self.recompute_stats()
        self.update_gauge_visual()

    def is_charged(self):
        return self.gauge >= GAUGE_MAX

    def delete(self):
        self.gauge_bg.delete()
        self.gauge_fill.delete()
        self.hp_badge.delete()
        self.hp_label.delete()
        self.atk_badge.delete()
        self.atk_label.delete()
        if self.sprite is not None:
            self.sprite.delete()
        if self.rect is not None:
            self.rect.delete()
        if self.label is not None:
            self.label.delete()


cards = []
occupied = {}


def spawn_initial_cards():
    tier1_numbers = sorted(CARD_CATALOG.get(1, {}).keys())
    if not tier1_numbers:
        return
    for row in PLAYER_ROWS.values():
        cols = random.sample(range(GRID_COLS), min(BORDER_CARD_COUNT, GRID_COLS))
        for col in cols:
            number = random.choice(tier1_numbers)
            card = Card(row, col, 1, number)
            cards.append(card)
            occupied[(row, col)] = card


selected_card = None
drag_dx = 0
drag_dy = 0
current_player = 1

ACTIVE_COLOR = (255, 255, 255, 255)
INACTIVE_COLOR = (110, 110, 110, 255)

player1_label = pyglet.text.Label(
    "Joueur 1",
    font_size=16,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=MARGIN / 2,
    anchor_x="center",
    anchor_y="center",
    color=ACTIVE_COLOR,
    batch=batch,
    group=label_group,
)
player2_label = pyglet.text.Label(
    "Joueur 2",
    font_size=16,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=WINDOW_HEIGHT - MARGIN / 2,
    anchor_x="center",
    anchor_y="center",
    color=INACTIVE_COLOR,
    batch=batch,
    group=label_group,
)


def update_player_labels():
    if current_player == 1:
        player1_label.color = ACTIVE_COLOR
        player2_label.color = INACTIVE_COLOR
    else:
        player1_label.color = INACTIVE_COLOR
        player2_label.color = ACTIVE_COLOR


def resolve_combat():
    """
    Tous les heros des deux lignes de devant attaquent, meme sans
    adversaire en face. Ordre : le plus a droite du joueur 1 attaque un
    ennemi au hasard chez le joueur 2, puis le plus a droite du joueur 2
    attaque un ennemi au hasard chez le joueur 1, et ainsi de suite en
    alternant et en remontant vers la gauche.
    """
    row1 = FRONT_ROWS[1]
    row2 = FRONT_ROWS[2]

    p1_heroes = sorted(
        (occupied[(row1, c)] for c in range(GRID_COLS) if (row1, c) in occupied),
        key=lambda card: card.col,
        reverse=True,
    )
    p2_heroes = sorted(
        (occupied[(row2, c)] for c in range(GRID_COLS) if (row2, c) in occupied),
        key=lambda card: card.col,
        reverse=True,
    )

    alive_p1 = list(p1_heroes)
    alive_p2 = list(p2_heroes)

    i = j = 0
    attacker_is_p1 = True
    while i < len(p1_heroes) or j < len(p2_heroes):
        if attacker_is_p1:
            if i < len(p1_heroes):
                attacker = p1_heroes[i]
                i += 1
                if attacker in alive_p1 and alive_p2:
                    target = random.choice(alive_p2)
                    target.hp -= attacker.atk
                    attacker.add_gauge(GAUGE_GAIN)
                    target.add_gauge(GAUGE_GAIN)
                    target.update_hp_label()
                    if target.hp <= 0:
                        alive_p2.remove(target)
        else:
            if j < len(p2_heroes):
                attacker = p2_heroes[j]
                j += 1
                if attacker in alive_p2 and alive_p1:
                    target = random.choice(alive_p1)
                    target.hp -= attacker.atk
                    attacker.add_gauge(GAUGE_GAIN)
                    target.add_gauge(GAUGE_GAIN)
                    target.update_hp_label()
                    if target.hp <= 0:
                        alive_p1.remove(target)
        attacker_is_p1 = not attacker_is_p1

    for hero in p1_heroes:
        if hero not in alive_p1:
            _remove_dead_hero(hero)
    for hero in p2_heroes:
        if hero not in alive_p2:
            _remove_dead_hero(hero)


def _remove_dead_hero(card):
    pos = (card.row, card.col)
    if occupied.get(pos) is card:
        del occupied[pos]
    if card in cards:
        cards.remove(card)
    card.delete()


def start_new_game():
    global current_player
    for card in cards:
        card.delete()
    cards.clear()
    occupied.clear()
    spawn_initial_cards()
    current_player = 1
    update_player_labels()


# --- Bouton generique (menu et index) -----------------------------------

class Button:
    def __init__(self, x, y, width, height, text, batch_, shape_group, text_group, font_size=20):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = shapes.BorderedRectangle(
            x, y, width, height,
            border=2,
            color=(50, 90, 160),
            border_color=(255, 255, 255),
            batch=batch_,
            group=shape_group,
        )
        self.label = pyglet.text.Label(
            text,
            font_size=font_size,
            weight="bold",
            x=x + width / 2,
            y=y + height / 2,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
            batch=batch_,
            group=text_group,
        )

    def contains(self, px, py):
        return (
            self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height
        )


# --- Bouton "passer le tour" (plateau de jeu) ----------------------------

PASS_BUTTON_WIDTH = 150
PASS_BUTTON_HEIGHT = 30

pass_button = Button(
    WINDOW_WIDTH - MARGIN - PASS_BUTTON_WIDTH,
    (MARGIN - PASS_BUTTON_HEIGHT) / 2,
    PASS_BUTTON_WIDTH,
    PASS_BUTTON_HEIGHT,
    "Passer le tour",
    batch,
    card_group,
    label_group,
    font_size=13,
)


def pass_turn():
    global current_player
    round_complete = current_player == 2
    current_player = 2 if current_player == 1 else 1
    if round_complete:
        resolve_combat()
    update_player_labels()


# --- Menu principal -------------------------------------------------------

menu_batch = pyglet.graphics.Batch()
menu_shape_group = pyglet.graphics.Group(order=0)
menu_text_group = pyglet.graphics.Group(order=1)

MENU_BUTTON_WIDTH = 280
MENU_BUTTON_HEIGHT = 60

menu_title = pyglet.text.Label(
    "BattleMerge",
    font_size=44,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=WINDOW_HEIGHT - 140,
    anchor_x="center",
    anchor_y="center",
    color=(255, 255, 255, 255),
    batch=menu_batch,
    group=menu_text_group,
)

play_button = Button(
    WINDOW_WIDTH / 2 - MENU_BUTTON_WIDTH / 2,
    WINDOW_HEIGHT / 2 + 10,
    MENU_BUTTON_WIDTH,
    MENU_BUTTON_HEIGHT,
    "Jouer",
    menu_batch,
    menu_shape_group,
    menu_text_group,
)

index_button = Button(
    WINDOW_WIDTH / 2 - MENU_BUTTON_WIDTH / 2,
    WINDOW_HEIGHT / 2 - 70,
    MENU_BUTTON_WIDTH,
    MENU_BUTTON_HEIGHT,
    "Index des heros",
    menu_batch,
    menu_shape_group,
    menu_text_group,
    font_size=18,
)


# --- Index des heros --------------------------------------------------

index_batch = pyglet.graphics.Batch()
index_shape_group = pyglet.graphics.Group(order=0)
index_text_group = pyglet.graphics.Group(order=1)

THUMB_SIZE = 110
THUMB_GAP = 20

index_title = pyglet.text.Label(
    "Index des heros",
    font_size=28,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=WINDOW_HEIGHT - 40,
    anchor_x="center",
    anchor_y="center",
    color=(255, 255, 255, 255),
    batch=index_batch,
    group=index_text_group,
)

back_button = Button(
    20, WINDOW_HEIGHT - 60, 120, 40, "Retour",
    index_batch, index_shape_group, index_text_group, font_size=14,
)

_index_visuals = []


def build_hero_index():
    heroes = [
        (tier, number)
        for tier in sorted(CARD_CATALOG.keys())
        for number in sorted(CARD_CATALOG[tier].keys())
    ]

    if not heroes:
        _index_visuals.append(
            pyglet.text.Label(
                "Aucun heros trouve dans assets/cards/",
                font_size=16,
                x=WINDOW_WIDTH / 2,
                y=WINDOW_HEIGHT / 2,
                anchor_x="center",
                anchor_y="center",
                color=(200, 200, 200, 255),
                batch=index_batch,
                group=index_text_group,
            )
        )
        return

    columns = max(1, (WINDOW_WIDTH - 2 * MARGIN + THUMB_GAP) // (THUMB_SIZE + THUMB_GAP))
    start_x = MARGIN
    top_y = WINDOW_HEIGHT - 100

    for i, (tier, number) in enumerate(heroes):
        col = i % columns
        row = i // columns
        x = start_x + col * (THUMB_SIZE + THUMB_GAP)
        y = top_y - row * (THUMB_SIZE + THUMB_GAP) - THUMB_SIZE

        image = get_card_image(tier, number)
        if image is not None:
            sprite = pyglet.sprite.Sprite(
                image, x=x, y=y, batch=index_batch, group=index_shape_group
            )
            sprite.scale_x = THUMB_SIZE / image.width
            sprite.scale_y = THUMB_SIZE / image.height
            _index_visuals.append(sprite)

        label = pyglet.text.Label(
            f"{tier}.{number}",
            font_size=14,
            weight="bold",
            x=x + THUMB_SIZE / 2,
            y=y - 14,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
            batch=index_batch,
            group=index_text_group,
        )
        _index_visuals.append(label)


build_hero_index()


# --- Etats de l'application ---------------------------------------------

STATE_MENU = "menu"
STATE_GAME = "game"
STATE_INDEX = "index"
state = STATE_MENU


@window.event
def on_draw():
    window.clear()
    if state == STATE_MENU:
        menu_batch.draw()
    elif state == STATE_GAME:
        batch.draw()
    elif state == STATE_INDEX:
        index_batch.draw()


@window.event
def on_mouse_press(x, y, button, modifiers):
    global selected_card, drag_dx, drag_dy, state
    if button != mouse.LEFT:
        return

    if state == STATE_MENU:
        if play_button.contains(x, y):
            start_new_game()
            state = STATE_GAME
        elif index_button.contains(x, y):
            state = STATE_INDEX
        return

    if state == STATE_INDEX:
        if back_button.contains(x, y):
            state = STATE_MENU
        return

    if pass_button.contains(x, y):
        pass_turn()
        return

    side_rows = PLAYER_SIDE_ROWS[current_player]
    for card in reversed(cards):
        if card.row in side_rows and card.contains_point(x, y):
            selected_card = card
            drag_dx = x - card.x
            drag_dy = y - card.y
            break


@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if state == STATE_GAME and selected_card is not None:
        selected_card.set_position_px(x - drag_dx, y - drag_dy)


@window.event
def on_mouse_release(x, y, button, modifiers):
    global selected_card, current_player
    if state != STATE_GAME or selected_card is None:
        return

    side_rows = PLAYER_SIDE_ROWS[current_player]
    center_x = selected_card.x + selected_card.width / 2
    center_y = selected_card.y + selected_card.height / 2
    row, col = pixel_to_cell(center_x, center_y)
    old_pos = (selected_card.row, selected_card.col)

    if row not in side_rows:
        # Hors de son propre cote : coup invalide.
        selected_card.snap_to_cell(*old_pos)
        selected_card = None
        return

    target = occupied.get((row, col))
    turn_used = False

    if target is None or target is selected_card:
        if (row, col) != old_pos:
            del occupied[old_pos]
            selected_card.snap_to_cell(row, col)
            occupied[(row, col)] = selected_card
            turn_used = True
        else:
            selected_card.snap_to_cell(*old_pos)
    else:
        result = merge_result(
            (selected_card.tier, selected_card.number), (target.tier, target.number)
        )
        if result is not None and selected_card.is_charged() and target.is_charged():
            result_tier, result_number = result
            del occupied[old_pos]
            cards.remove(selected_card)
            cards.remove(target)
            selected_card.delete()
            target.delete()
            merged = Card(row, col, result_tier, result_number)
            cards.append(merged)
            occupied[(row, col)] = merged
            turn_used = True
        else:
            selected_card.snap_to_cell(*old_pos)

    selected_card = None

    if turn_used:
        round_complete = current_player == 2
        current_player = 2 if current_player == 1 else 1
        if round_complete:
            resolve_combat()
        update_player_labels()


if __name__ == "__main__":
    pyglet.app.run()
