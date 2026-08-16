import random
import re
from pathlib import Path

import pyglet
from pyglet import gl, shapes
from pyglet.window import mouse

from fusions import FUSIONS
from stats import STATS
from specialties import SPECIALTIES
from abilities import CLASS_ABILITIES
from items import ITEMS

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

# Un heros sur la ligne d'extremite (son bord du plateau) regagne des
# PV chaque round, en pourcentage de sa vie de base.
BACK_ROW_HEAL_RATIO = 0.15

# Ligne du bord (spawn) de chaque joueur : joueur 1 en bas, joueur 2 en haut.
PLAYER_ROWS = {1: 0, 2: GRID_ROWS - 1}
# Ligne de devant (front line) de chaque joueur, au milieu du plateau.
FRONT_ROWS = {1: 1, 2: GRID_ROWS - 2}
# Toutes les lignes qu'un joueur peut jouer sur son tour (son cote).
PLAYER_SIDE_ROWS = {
    player: {PLAYER_ROWS[player], FRONT_ROWS[player]} for player in (1, 2)
}
# Ordre de preference pour placer un heros recrute (ligne du fond d'abord).
PLAYER_SPAWN_ORDER = {
    player: [PLAYER_ROWS[player], FRONT_ROWS[player]] for player in (1, 2)
}

# Points de mouvement : +1 par tour (plafonne), cout des actions, et or.
MAX_MOVEMENT = 5
MOVE_COST = 1
FUSE_COST = 3
RECRUIT_GOLD_COST = 100
RECRUIT_MOVEMENT_COST = 1
KILL_GOLD_REWARD = 200

PLAYER_MOVEMENT = {1: 0, 2: 0}
PLAYER_GOLD = {1: 0, 2: 0}
# Nombre de tours joues par chaque joueur (sert a calculer ses PM).
PLAYER_TURN_COUNT = {1: 0, 2: 0}

# Objets : grille 3x3 par joueur, remplie par les reliques lachees en
# tuant un ennemi. Chaque case contient une cle (tier, numero) d'ITEMS
# ou None.
INVENTORY_SIZE = 9
PLAYER_INVENTORY = {1: [None] * INVENTORY_SIZE, 2: [None] * INVENTORY_SIZE}
ITEM_SLOT_SIZE = 60
ITEM_SLOT_GAP = 6

# Joueur dont c'est le tour. Defini tot car cell_rect() en a besoin pour
# afficher le plateau retourne du point de vue du joueur actif.
current_player = 1

CELL_GAP = 6
# Marge horizontale du plateau (plus large que la marge verticale pour
# laisser de la place a la mine et au camp d'entrainement sur les cotes).
BOARD_MARGIN_X = 150

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

board_width = WINDOW_WIDTH - 2 * BOARD_MARGIN_X
board_height = WINDOW_HEIGHT - 2 * MARGIN
cell_width = (board_width - (GRID_COLS - 1) * CELL_GAP) / GRID_COLS
cell_height = (board_height - (GRID_ROWS - 1) * CELL_GAP) / GRID_ROWS


def display_row(row):
    """
    Rang a l'ecran pour une ligne logique donnee : le plateau est
    affiche du point de vue du joueur actif, qui est toujours en bas.
    """
    if current_player == 1:
        return row
    return GRID_ROWS - 1 - row


def cell_rect(row, col):
    d_row = display_row(row)
    x = BOARD_MARGIN_X + col * (cell_width + CELL_GAP)
    y = MARGIN + d_row * (cell_height + CELL_GAP)
    return x, y, cell_width, cell_height


def pixel_to_cell(px, py):
    col = int((px - BOARD_MARGIN_X) // (cell_width + CELL_GAP))
    d_row = int((py - MARGIN) // (cell_height + CELL_GAP))
    col = max(0, min(GRID_COLS - 1, col))
    d_row = max(0, min(GRID_ROWS - 1, d_row))
    row = d_row if current_player == 1 else GRID_ROWS - 1 - d_row
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


# --- Batiments : mine (gauche) et camp d'entrainement (droite) ----------
# Toujours en bas de l'ecran, cote du joueur actif (le plateau se
# retourne). Un heros glisse dedans depuis le plateau pour y etre
# assigne ; chaque round, la mine rapporte de l'or au prix d'un peu de
# vie de chaque heros assigne, le camp d'entrainement rapporte de l'XP
# (jauge de charge) au prix d'un peu d'or. Chaque batiment commence avec
# une place et peut etre ameliore (contre de l'or) jusqu'a 3 places.

MINE_GOLD_GAIN = 40
MINE_HP_LOSS = 6
TRAINING_GOLD_COST = 30
TRAINING_XP_GAIN = 25

BUILDING_MAX_CAPACITY = 3
MINE_UPGRADE_COST = {2: 150, 3: 300}
CAMP_UPGRADE_COST = {2: 150, 3: 300}

BUILDING_BOX_Y = MARGIN
mine_box_x = (BOARD_MARGIN_X - cell_width) / 2
camp_box_x = WINDOW_WIDTH - BOARD_MARGIN_X + (BOARD_MARGIN_X - cell_width) / 2

MINE_CAPACITY = {1: 1, 2: 1}
CAMP_CAPACITY = {1: 1, 2: 1}
# Une liste de longueur BUILDING_MAX_CAPACITY par joueur ; les emplacements
# au-dela de la capacite actuelle restent None tant qu'ils ne sont pas
# debloques par une amelioration.
MINE_ASSIGNMENTS = {1: [None] * BUILDING_MAX_CAPACITY, 2: [None] * BUILDING_MAX_CAPACITY}
CAMP_ASSIGNMENTS = {1: [None] * BUILDING_MAX_CAPACITY, 2: [None] * BUILDING_MAX_CAPACITY}


def rect_contains(x, y, width, height, px, py):
    return x <= px <= x + width and y <= py <= y + height


def building_slot_rect(building, index):
    box_x = mine_box_x if building == "mine" else camp_box_x
    y = BUILDING_BOX_Y + index * (cell_height + CELL_GAP)
    return box_x, y, cell_width, cell_height


def building_zone_rect(building):
    box_x = mine_box_x if building == "mine" else camp_box_x
    height = BUILDING_MAX_CAPACITY * (cell_height + CELL_GAP) - CELL_GAP
    return box_x, BUILDING_BOX_Y, cell_width, height


UNLOCKED_COLORS = {
    "mine": ((45, 35, 15), (200, 160, 60)),
    "camp": ((15, 35, 45), (60, 170, 220)),
}
LOCKED_COLOR = (25, 25, 28)
LOCKED_BORDER = (70, 70, 75)

mine_slot_boxes = []
camp_slot_boxes = []
for _i in range(BUILDING_MAX_CAPACITY):
    _x, _y, _w, _h = building_slot_rect("mine", _i)
    mine_slot_boxes.append(
        shapes.BorderedRectangle(
            _x, _y, _w, _h, border=2,
            color=UNLOCKED_COLORS["mine"][0], border_color=UNLOCKED_COLORS["mine"][1],
            batch=batch, group=cell_group,
        )
    )
    _x, _y, _w, _h = building_slot_rect("camp", _i)
    camp_slot_boxes.append(
        shapes.BorderedRectangle(
            _x, _y, _w, _h, border=2,
            color=UNLOCKED_COLORS["camp"][0], border_color=UNLOCKED_COLORS["camp"][1],
            batch=batch, group=cell_group,
        )
    )

BUILDING_TITLE_Y = BUILDING_BOX_Y + BUILDING_MAX_CAPACITY * (cell_height + CELL_GAP) + 14
BUILDING_UPGRADE_Y = BUILDING_TITLE_Y + 22

mine_label = pyglet.text.Label(
    "Mine",
    font_size=13,
    weight="bold",
    x=mine_box_x + cell_width / 2,
    y=BUILDING_TITLE_Y,
    anchor_x="center",
    anchor_y="center",
    color=(230, 190, 90, 255),
    batch=batch,
    group=label_group,
)
camp_label = pyglet.text.Label(
    "Camp",
    font_size=13,
    weight="bold",
    x=camp_box_x + cell_width / 2,
    y=BUILDING_TITLE_Y,
    anchor_x="center",
    anchor_y="center",
    color=(120, 210, 240, 255),
    batch=batch,
    group=label_group,
)


class Card:
    def __init__(self, row, col, tier, number):
        self.row = row
        self.col = col
        self.tier = tier
        self.number = number
        # None si sur le plateau, sinon "mine" ou "camp".
        self.building = None
        self.building_slot = None  # index dans la liste d'assignation
        # Cle (tier, numero) de l'objet equipe, ou None.
        self.equipped_item = None
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

        # Petit badge en haut a droite, visible seulement si un objet
        # est equipe.
        self.item_badge = pyglet.text.Label(
            "",
            font_size=13,
            weight="bold",
            x=self.x + self.width - 10,
            y=self.y + self.height - 10,
            anchor_x="center",
            anchor_y="center",
            color=(255, 230, 80, 255),
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

        self.item_badge.x = x + self.width - 10
        self.item_badge.y = y + self.height - 10

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

    def update_item_badge(self):
        self.item_badge.text = "*" if self.equipped_item is not None else ""

    def delete(self):
        self.gauge_bg.delete()
        self.gauge_fill.delete()
        self.hp_badge.delete()
        self.hp_label.delete()
        self.atk_badge.delete()
        self.atk_label.delete()
        self.item_badge.delete()
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


def position_in_building(card, building, index):
    box_x, box_y, _w, _h = building_slot_rect(building, index)
    card.set_position_px(box_x + CARD_MARGIN, box_y + CARD_MARGIN)


def refresh_card_positions():
    """
    Replace toutes les cartes a l'ecran selon le retournement actuel.
    Les heros assignes a un batiment du joueur inactif sont envoyes hors
    ecran (seul le batiment du joueur actif est visible a la fois).
    """
    for card in cards:
        if card.building is None:
            card.snap_to_cell(card.row, card.col)

    for player in (1, 2):
        for building, assignments in (("mine", MINE_ASSIGNMENTS), ("camp", CAMP_ASSIGNMENTS)):
            for index, card in enumerate(assignments[player]):
                if card is None:
                    continue
                if player == current_player:
                    position_in_building(card, building, index)
                else:
                    card.set_position_px(-9999, -9999)


selected_card = None
drag_dx = 0
drag_dy = 0

# Le plateau se retourne pour que le joueur actif soit toujours en bas :
# un seul message d'annonce de tour (en haut) et un seul statut PM/or
# (en bas, pres des boutons) suffisent, plus besoin d'un jeu par joueur.
turn_label = pyglet.text.Label(
    "Au tour de Joueur 1",
    font_size=20,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=WINDOW_HEIGHT - MARGIN / 2,
    anchor_x="center",
    anchor_y="center",
    color=(255, 255, 255, 255),
    batch=batch,
    group=label_group,
)
status_label = pyglet.text.Label(
    "PM 0  |  Or 0",
    font_size=16,
    weight="bold",
    x=MARGIN + 100,
    y=MARGIN / 2,
    anchor_x="center",
    anchor_y="center",
    color=(255, 255, 255, 255),
    batch=batch,
    group=label_group,
)


def update_turn_ui():
    turn_label.text = f"Au tour de Joueur {current_player}"
    status_label.text = (
        f"PM {PLAYER_MOVEMENT[current_player]}  |  Or {PLAYER_GOLD[current_player]}"
    )


def start_turn(player):
    """
    Les PM d'un joueur valent le nombre de tours qu'il a joues (1 a son
    premier tour, 2 au deuxieme, etc.), plafonne a MAX_MOVEMENT. Ca
    grimpe donc de 1 par tour, meme si les points precedents ont ete
    depenses.
    """
    PLAYER_TURN_COUNT[player] += 1
    PLAYER_MOVEMENT[player] = min(MAX_MOVEMENT, PLAYER_TURN_COUNT[player])


# --- Capacites de classe : logique de jeu -------------------------------

ABILITY_EXECUTE_THRESHOLD = 0.5
ABILITY_CLEAVE_RATIO = 0.5
ABILITY_SELF_GROWTH_HP = 5
ABILITY_SELF_GROWTH_ATK = 2
ABILITY_RALLY_BONUS = 15


def get_ability(card):
    specialty = SPECIALTIES.get((card.tier, card.number))
    return CLASS_ABILITIES.get(specialty)


def has_effect(card, effect):
    ability = get_ability(card)
    return ability is not None and ability["effect"] == effect


def get_ability_value(card):
    """
    Valeur de la capacite de classe de ce heros precis. Si l'objet
    equipe correspond a ce heros (meme tier et numero), sa capacite est
    boostee par le "passive_boost" de l'objet.
    """
    ability = get_ability(card)
    if ability is None:
        return 0
    value = ability.get("value", 0)
    if card.equipped_item == (card.tier, card.number):
        item = ITEMS.get(card.equipped_item)
        if item:
            value *= 1 + item.get("passive_boost", 0)
    return value


def pick_target(attacker, alive_enemies):
    taunters = [h for h in alive_enemies if has_effect(h, "taunt")]
    if taunters:
        return random.choice(taunters)
    if has_effect(attacker, "target_weakest"):
        return min(alive_enemies, key=lambda h: h.hp)
    return random.choice(alive_enemies)


def compute_damage(attacker, target):
    damage = attacker.atk
    ability = get_ability(attacker)
    if ability:
        effect = ability["effect"]
        value = get_ability_value(attacker)
        if effect == "bonus_damage":
            damage *= 1 + value
        elif effect == "bonus_vs_full_hp" and target.hp >= target.effective_max_hp:
            damage *= 1 + value
        elif effect == "execute" and target.hp <= target.effective_max_hp * ABILITY_EXECUTE_THRESHOLD:
            damage *= 1 + value
        elif effect == "rage" and attacker.effective_max_hp:
            missing_ratio = 1 - max(attacker.hp, 0) / attacker.effective_max_hp
            damage *= 1 + value * missing_ratio
    return max(0, round(damage))


def shield_reduction(defender_side_alive):
    reduction = 0
    for ally in defender_side_alive:
        if has_effect(ally, "damage_shield"):
            reduction = max(reduction, get_ability_value(ally))
    return reduction


def apply_on_hit(attacker, target, attacker_player):
    ability = get_ability(attacker)
    if ability is None:
        return
    effect = ability["effect"]
    value = get_ability_value(attacker)
    if effect == "weaken":
        target.base_atk = max(0, round(target.base_atk * (1 - value)))
        target.recompute_stats()
    elif effect == "gold_steal":
        opponent = 2 if attacker_player == 1 else 1
        stolen = min(value, PLAYER_GOLD[opponent])
        PLAYER_GOLD[opponent] -= stolen
        PLAYER_GOLD[attacker_player] += stolen


def heal_most_wounded(healer, allies_alive):
    wounded = [a for a in allies_alive if a.hp < a.effective_max_hp]
    if not wounded:
        return
    target = min(wounded, key=lambda a: a.hp / a.effective_max_hp)
    heal = round(target.effective_max_hp * get_ability_value(healer))
    target.hp = min(target.effective_max_hp, target.hp + heal)
    target.update_hp_label()


def try_revive(dead_card, side_alive):
    revivers = [a for a in side_alive if has_effect(a, "revive")]
    if not revivers:
        return False
    reviver_value = get_ability_value(revivers[0])
    if random.random() >= reviver_value:
        return False
    dead_card.hp = max(1, round(dead_card.effective_max_hp * 0.3))
    dead_card.update_hp_label()
    return True


def drop_item(card, player):
    """Le heros tombe au combat lache sa relique dans l'inventaire du tueur."""
    if (card.tier, card.number) not in ITEMS:
        return
    inventory = PLAYER_INVENTORY[player]
    for i in range(INVENTORY_SIZE):
        if inventory[i] is None:
            inventory[i] = (card.tier, card.number)
            return


def handle_potential_death(card, side_alive, attacker_player):
    if card.hp > 0:
        return False
    if try_revive(card, side_alive):
        return False
    if card in side_alive:
        side_alive.remove(card)
    PLAYER_GOLD[attacker_player] += KILL_GOLD_REWARD
    drop_item(card, attacker_player)
    return True


def execute_attack(attacker, attacker_player, allies_alive, enemy_alive):
    if has_effect(attacker, "heal_ally"):
        heal_most_wounded(attacker, allies_alive)
        attacker.add_gauge(GAUGE_GAIN)
        return

    attacks = 2 if has_effect(attacker, "double_attack") else 1
    for _ in range(attacks):
        if not enemy_alive:
            return

        target = pick_target(attacker, enemy_alive)
        damage = compute_damage(attacker, target)
        damage = round(damage * (1 - shield_reduction(enemy_alive)))

        dodged = has_effect(target, "dodge") and random.random() < get_ability_value(target)
        if not dodged:
            target.hp -= damage
            apply_on_hit(attacker, target, attacker_player)
            target.add_gauge(GAUGE_GAIN)
        target.update_hp_label()

        attacker.add_gauge(GAUGE_GAIN * (2 if has_effect(attacker, "fast_charge") else 1))

        if dodged:
            continue

        if target.hp <= 0:
            overkill = -target.hp
            died = handle_potential_death(target, enemy_alive, attacker_player)
            if died and has_effect(attacker, "overkill") and overkill > 0 and enemy_alive:
                second = random.choice(enemy_alive)
                second.hp -= overkill
                second.update_hp_label()
                handle_potential_death(second, enemy_alive, attacker_player)

        if has_effect(attacker, "cleave") and enemy_alive:
            others = [h for h in enemy_alive if h is not target]
            if others:
                second = random.choice(others)
                second.hp -= round(damage * ABILITY_CLEAVE_RATIO)
                second.update_hp_label()
                if second.hp <= 0:
                    handle_potential_death(second, enemy_alive, attacker_player)


def apply_rally_bonus(alive_p1, alive_p2):
    for side in (alive_p1, alive_p2):
        if any(has_effect(c, "rally") for c in side):
            for c in side:
                c.add_gauge(ABILITY_RALLY_BONUS)


def apply_self_growth(alive_p1, alive_p2):
    for card in alive_p1 + alive_p2:
        if has_effect(card, "self_growth"):
            card.base_hp += ABILITY_SELF_GROWTH_HP
            card.base_atk += ABILITY_SELF_GROWTH_ATK
            card.recompute_stats()


def resolve_combat():
    """
    Tous les heros des deux lignes de devant attaquent, meme sans
    adversaire en face. Ordre : le plus a droite du joueur 1 attaque un
    ennemi chez le joueur 2, puis le plus a droite du joueur 2 attaque
    un ennemi chez le joueur 1, et ainsi de suite en alternant et en
    remontant vers la gauche. La cible et les degats exacts dependent
    de la capacite de classe de chaque heros (voir abilities.py).
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
                if attacker in alive_p1:
                    execute_attack(attacker, 1, alive_p1, alive_p2)
        else:
            if j < len(p2_heroes):
                attacker = p2_heroes[j]
                j += 1
                if attacker in alive_p2:
                    execute_attack(attacker, 2, alive_p2, alive_p1)
        attacker_is_p1 = not attacker_is_p1

    for hero in p1_heroes:
        if hero not in alive_p1:
            _remove_dead_hero(hero)
    for hero in p2_heroes:
        if hero not in alive_p2:
            _remove_dead_hero(hero)

    apply_back_row_regen()
    apply_rally_bonus(alive_p1, alive_p2)
    apply_self_growth(alive_p1, alive_p2)
    apply_building_income()
    update_turn_ui()


def apply_building_income():
    """La mine rapporte de l'or contre un peu de vie, le camp de l'XP contre de l'or."""
    for player in (1, 2):
        for index, mine_card in enumerate(MINE_ASSIGNMENTS[player]):
            if mine_card is None:
                continue
            PLAYER_GOLD[player] += MINE_GOLD_GAIN
            mine_card.hp -= MINE_HP_LOSS
            mine_card.update_hp_label()
            if mine_card.hp <= 0:
                MINE_ASSIGNMENTS[player][index] = None
                if mine_card in cards:
                    cards.remove(mine_card)
                mine_card.delete()

        for camp_card in CAMP_ASSIGNMENTS[player]:
            if camp_card is not None and PLAYER_GOLD[player] >= TRAINING_GOLD_COST:
                PLAYER_GOLD[player] -= TRAINING_GOLD_COST
                camp_card.add_gauge(TRAINING_XP_GAIN)


def apply_back_row_regen():
    """Les heros sur la ligne d'extremite de leur camp regagnent des PV."""
    for player in (1, 2):
        row = PLAYER_ROWS[player]
        for col in range(GRID_COLS):
            card = occupied.get((row, col))
            if card is None:
                continue
            heal = round(card.base_hp * BACK_ROW_HEAL_RATIO)
            if heal <= 0 or card.hp >= card.effective_max_hp:
                continue
            card.hp = min(card.effective_max_hp, card.hp + heal)
            card.update_hp_label()


def _remove_dead_hero(card):
    pos = (card.row, card.col)
    if occupied.get(pos) is card:
        del occupied[pos]
    if card in cards:
        cards.remove(card)
    card.delete()


def start_new_game():
    global current_player, pending_equip_item, selected_inventory_slot
    for card in cards:
        card.delete()
    cards.clear()
    occupied.clear()
    PLAYER_INVENTORY[1] = [None] * INVENTORY_SIZE
    PLAYER_INVENTORY[2] = [None] * INVENTORY_SIZE
    pending_equip_item = None
    selected_inventory_slot = None
    MINE_ASSIGNMENTS[1] = [None] * BUILDING_MAX_CAPACITY
    MINE_ASSIGNMENTS[2] = [None] * BUILDING_MAX_CAPACITY
    CAMP_ASSIGNMENTS[1] = [None] * BUILDING_MAX_CAPACITY
    CAMP_ASSIGNMENTS[2] = [None] * BUILDING_MAX_CAPACITY
    MINE_CAPACITY[1] = 1
    MINE_CAPACITY[2] = 1
    CAMP_CAPACITY[1] = 1
    CAMP_CAPACITY[2] = 1
    spawn_initial_cards()
    current_player = 1
    PLAYER_MOVEMENT[1] = 0
    PLAYER_MOVEMENT[2] = 0
    PLAYER_GOLD[1] = 0
    PLAYER_GOLD[2] = 0
    PLAYER_TURN_COUNT[1] = 0
    PLAYER_TURN_COUNT[2] = 0
    start_turn(current_player)
    refresh_building_visuals()
    update_turn_ui()


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


# --- Boutons "passer le tour" / "recruter" -------------------------------
# Un seul jeu de boutons, toujours en bas : le plateau se retourne pour
# que ce soit toujours la ligne du joueur actif.

PASS_BUTTON_WIDTH = 150
PASS_BUTTON_HEIGHT = 30
RECRUIT_BUTTON_WIDTH = 170
RECRUIT_BUTTON_HEIGHT = 30
BUTTON_ROW_GAP = 10

pass_x = WINDOW_WIDTH - MARGIN - PASS_BUTTON_WIDTH
recruit_x = pass_x - RECRUIT_BUTTON_WIDTH - BUTTON_ROW_GAP
buttons_y = (MARGIN - PASS_BUTTON_HEIGHT) / 2

pass_button = Button(
    pass_x, buttons_y, PASS_BUTTON_WIDTH, PASS_BUTTON_HEIGHT,
    "Passer le tour", batch, card_group, label_group, font_size=13,
)
recruit_button = Button(
    recruit_x, buttons_y, RECRUIT_BUTTON_WIDTH, RECRUIT_BUTTON_HEIGHT,
    "Recruter (100 or)", batch, card_group, label_group, font_size=13,
)

INVENTORY_BUTTON_WIDTH = 130
inventory_button_x = recruit_x - INVENTORY_BUTTON_WIDTH - BUTTON_ROW_GAP
inventory_button = Button(
    inventory_button_x, buttons_y, INVENTORY_BUTTON_WIDTH, PASS_BUTTON_HEIGHT,
    "Inventaire", batch, card_group, label_group, font_size=13,
)

mine_upgrade_button = Button(
    mine_box_x, BUILDING_UPGRADE_Y, cell_width, 24,
    "+1 place", batch, card_group, label_group, font_size=9,
)
camp_upgrade_button = Button(
    camp_box_x, BUILDING_UPGRADE_Y, cell_width, 24,
    "+1 place", batch, card_group, label_group, font_size=9,
)


def refresh_building_visuals():
    for index, box in enumerate(mine_slot_boxes):
        if index < MINE_CAPACITY[current_player]:
            color, border = UNLOCKED_COLORS["mine"]
        else:
            color, border = LOCKED_COLOR, LOCKED_BORDER
        box.color = color
        box.border_color = border

    for index, box in enumerate(camp_slot_boxes):
        if index < CAMP_CAPACITY[current_player]:
            color, border = UNLOCKED_COLORS["camp"]
        else:
            color, border = LOCKED_COLOR, LOCKED_BORDER
        box.color = color
        box.border_color = border

    mine_cap = MINE_CAPACITY[current_player]
    mine_upgrade_button.label.text = (
        "Mine max" if mine_cap >= BUILDING_MAX_CAPACITY
        else f"+1 place ({MINE_UPGRADE_COST[mine_cap + 1]}o)"
    )

    camp_cap = CAMP_CAPACITY[current_player]
    camp_upgrade_button.label.text = (
        "Camp max" if camp_cap >= BUILDING_MAX_CAPACITY
        else f"+1 place ({CAMP_UPGRADE_COST[camp_cap + 1]}o)"
    )


def upgrade_building(building):
    player = current_player
    capacity = MINE_CAPACITY if building == "mine" else CAMP_CAPACITY
    cost_table = MINE_UPGRADE_COST if building == "mine" else CAMP_UPGRADE_COST

    current_capacity = capacity[player]
    if current_capacity >= BUILDING_MAX_CAPACITY:
        return
    cost = cost_table[current_capacity + 1]
    if PLAYER_GOLD[player] < cost:
        return

    PLAYER_GOLD[player] -= cost
    capacity[player] = current_capacity + 1
    refresh_building_visuals()
    update_turn_ui()


def pass_turn():
    global current_player
    round_complete = current_player == 2
    current_player = 2 if current_player == 1 else 1
    refresh_card_positions()
    refresh_building_visuals()
    start_turn(current_player)
    if round_complete:
        resolve_combat()
    update_turn_ui()


def recruit_hero():
    player = current_player
    if PLAYER_GOLD[player] < RECRUIT_GOLD_COST:
        return
    if PLAYER_MOVEMENT[player] < RECRUIT_MOVEMENT_COST:
        return
    tier1_numbers = sorted(CARD_CATALOG.get(1, {}).keys())
    if not tier1_numbers:
        return

    free_cell = None
    for row in PLAYER_SPAWN_ORDER[player]:
        for col in range(GRID_COLS):
            if (row, col) not in occupied:
                free_cell = (row, col)
                break
        if free_cell is not None:
            break
    if free_cell is None:
        return

    row, col = free_cell
    number = random.choice(tier1_numbers)
    card = Card(row, col, 1, number)
    cards.append(card)
    occupied[(row, col)] = card

    PLAYER_GOLD[player] -= RECRUIT_GOLD_COST
    PLAYER_MOVEMENT[player] -= RECRUIT_MOVEMENT_COST
    update_turn_ui()


# --- Objets : equiper / vendre --------------------------------------------

# Objet en attente d'etre pose sur un heros (choisi depuis l'inventaire).
pending_equip_item = None


def apply_item_stats(card, item_key, sign):
    item = ITEMS.get(item_key)
    if not item:
        return
    card.base_hp += sign * item.get("hp_bonus", 0)
    card.base_atk += sign * item.get("atk_bonus", 0)
    card.recompute_stats()


def equip_item_on_card(card, item_key):
    if card.equipped_item is not None:
        return False
    apply_item_stats(card, item_key, 1)
    card.equipped_item = item_key
    card.update_item_badge()
    return True


def sell_item(player, slot_index):
    item_key = PLAYER_INVENTORY[player][slot_index]
    if item_key is None:
        return
    item = ITEMS.get(item_key)
    PLAYER_GOLD[player] += item.get("sell_value", 0) if item else 0
    PLAYER_INVENTORY[player][slot_index] = None
    update_turn_ui()


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
# index_batch : elements fixes (titre, bouton retour).
# index_content_batch : grille des heros, qui defile (scroll molette).

index_batch = pyglet.graphics.Batch()
index_content_batch = pyglet.graphics.Batch()
index_shape_group = pyglet.graphics.Group(order=0)
index_text_group = pyglet.graphics.Group(order=1)

THUMB_SIZE = 110
THUMB_GAP = 90
INDEX_CONTENT_TOP = WINDOW_HEIGHT - 100
INDEX_CONTENT_BOTTOM = 20
INDEX_SCROLL_SPEED = 30

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

index_tab_button = Button(
    WINDOW_WIDTH - 20 - 160, WINDOW_HEIGHT - 60, 160, 40, "Voir les objets",
    index_batch, index_shape_group, index_text_group, font_size=13,
)

index_mode = "heroes"

_index_visuals = []
# (visual, y_de_base) pour chaque element qui doit suivre le defilement.
_index_scroll_items = []
index_scroll_offset = 0
index_max_scroll = 0


def build_hero_index():
    global index_max_scroll

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
    rows = -(-len(heroes) // columns)  # ceil
    start_x = MARGIN
    top_y = INDEX_CONTENT_TOP

    for i, (tier, number) in enumerate(heroes):
        col = i % columns
        row = i // columns
        x = start_x + col * (THUMB_SIZE + THUMB_GAP)
        y = top_y - row * (THUMB_SIZE + THUMB_GAP) - THUMB_SIZE

        image = get_card_image(tier, number)
        if image is not None:
            sprite = pyglet.sprite.Sprite(
                image, x=x, y=y, batch=index_content_batch, group=index_shape_group
            )
            sprite.scale_x = THUMB_SIZE / image.width
            sprite.scale_y = THUMB_SIZE / image.height
            _index_visuals.append(sprite)
            _index_scroll_items.append((sprite, y))

        id_label = pyglet.text.Label(
            f"{tier}.{number}",
            font_size=14,
            weight="bold",
            x=x + THUMB_SIZE / 2,
            y=y - 14,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
            batch=index_content_batch,
            group=index_text_group,
        )
        _index_visuals.append(id_label)
        _index_scroll_items.append((id_label, y - 14))

        specialty = SPECIALTIES.get((tier, number), "")
        specialty_label = pyglet.text.Label(
            specialty,
            font_size=12,
            italic=True,
            x=x + THUMB_SIZE / 2,
            y=y - 32,
            anchor_x="center",
            anchor_y="center",
            color=(180, 200, 255, 255),
            batch=index_content_batch,
            group=index_text_group,
        )
        _index_visuals.append(specialty_label)
        _index_scroll_items.append((specialty_label, y - 32))

        ability_label = pyglet.text.Label(
            CLASS_ABILITIES.get(specialty, {}).get("description", ""),
            font_size=9,
            x=x + THUMB_SIZE / 2,
            y=y - 46,
            width=THUMB_SIZE + THUMB_GAP - 12,
            multiline=True,
            align="center",
            anchor_x="center",
            anchor_y="top",
            color=(200, 200, 200, 255),
            batch=index_content_batch,
            group=index_text_group,
        )
        _index_visuals.append(ability_label)
        _index_scroll_items.append((ability_label, y - 46))

    content_height = rows * (THUMB_SIZE + THUMB_GAP)
    visible_height = INDEX_CONTENT_TOP - INDEX_CONTENT_BOTTOM
    index_max_scroll = max(0, content_height - visible_height)


def build_item_index():
    global index_max_scroll

    item_keys = [
        (tier, number)
        for tier in sorted(CARD_CATALOG.keys())
        for number in sorted(CARD_CATALOG[tier].keys())
        if (tier, number) in ITEMS
    ]

    if not item_keys:
        _index_visuals.append(
            pyglet.text.Label(
                "Aucun objet defini dans items.py",
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
    rows = -(-len(item_keys) // columns)
    start_x = MARGIN
    top_y = INDEX_CONTENT_TOP

    for i, key in enumerate(item_keys):
        item = ITEMS[key]
        col = i % columns
        row = i // columns
        x = start_x + col * (THUMB_SIZE + THUMB_GAP)
        y = top_y - row * (THUMB_SIZE + THUMB_GAP) - THUMB_SIZE

        image = get_card_image(*key)
        if image is not None:
            sprite = pyglet.sprite.Sprite(
                image, x=x, y=y, batch=index_content_batch, group=index_shape_group
            )
            sprite.scale_x = THUMB_SIZE / image.width
            sprite.scale_y = THUMB_SIZE / image.height
            _index_visuals.append(sprite)
            _index_scroll_items.append((sprite, y))

        name_label = pyglet.text.Label(
            item["name"],
            font_size=13,
            weight="bold",
            x=x + THUMB_SIZE / 2,
            y=y - 14,
            width=THUMB_SIZE + THUMB_GAP - 12,
            multiline=True,
            align="center",
            anchor_x="center",
            anchor_y="top",
            color=(255, 230, 140, 255),
            batch=index_content_batch,
            group=index_text_group,
        )
        _index_visuals.append(name_label)
        _index_scroll_items.append((name_label, y - 14))

        desc_label = pyglet.text.Label(
            item["description"],
            font_size=9,
            x=x + THUMB_SIZE / 2,
            y=y - 46,
            width=THUMB_SIZE + THUMB_GAP - 12,
            multiline=True,
            align="center",
            anchor_x="center",
            anchor_y="top",
            color=(200, 200, 200, 255),
            batch=index_content_batch,
            group=index_text_group,
        )
        _index_visuals.append(desc_label)
        _index_scroll_items.append((desc_label, y - 46))

        sell_label = pyglet.text.Label(
            f"Vente : {item.get('sell_value', 0)} or",
            font_size=9,
            weight="bold",
            x=x + THUMB_SIZE / 2,
            y=y - 82,
            anchor_x="center",
            anchor_y="top",
            color=(230, 190, 90, 255),
            batch=index_content_batch,
            group=index_text_group,
        )
        _index_visuals.append(sell_label)
        _index_scroll_items.append((sell_label, y - 82))

    content_height = rows * (THUMB_SIZE + THUMB_GAP)
    visible_height = INDEX_CONTENT_TOP - INDEX_CONTENT_BOTTOM
    index_max_scroll = max(0, content_height - visible_height)


def clear_index_content():
    global index_scroll_offset
    for visual in _index_visuals:
        visual.delete()
    _index_visuals.clear()
    _index_scroll_items.clear()
    index_scroll_offset = 0


def switch_index_mode():
    global index_mode
    clear_index_content()
    if index_mode == "heroes":
        index_mode = "items"
        index_title.text = "Index des objets"
        index_tab_button.label.text = "Voir les heros"
        build_item_index()
    else:
        index_mode = "heroes"
        index_title.text = "Index des heros"
        index_tab_button.label.text = "Voir les objets"
        build_hero_index()


def apply_index_scroll():
    for visual, base_y in _index_scroll_items:
        visual.y = base_y + index_scroll_offset


def scroll_index(dy):
    global index_scroll_offset
    index_scroll_offset = max(0, min(index_max_scroll, index_scroll_offset + dy))
    apply_index_scroll()


build_hero_index()


# --- Inventaire : equiper ou vendre les objets recuperes -----------------

inventory_batch = pyglet.graphics.Batch()
inventory_shape_group = pyglet.graphics.Group(order=0)
inventory_text_group = pyglet.graphics.Group(order=1)

inventory_title = pyglet.text.Label(
    "Inventaire",
    font_size=28,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=WINDOW_HEIGHT - 40,
    anchor_x="center",
    anchor_y="center",
    color=(255, 255, 255, 255),
    batch=inventory_batch,
    group=inventory_text_group,
)

inventory_back_button = Button(
    20, WINDOW_HEIGHT - 60, 120, 40, "Retour",
    inventory_batch, inventory_shape_group, inventory_text_group, font_size=14,
)

INV_SLOT_SIZE = 90
INV_SLOT_GAP = 14
INV_GRID_COLS = 3
_inv_grid_width = INV_GRID_COLS * INV_SLOT_SIZE + (INV_GRID_COLS - 1) * INV_SLOT_GAP
INV_GRID_X = (WINDOW_WIDTH - _inv_grid_width) / 2
INV_GRID_TOP_Y = WINDOW_HEIGHT - 140

inventory_slot_boxes = []
for _i in range(INVENTORY_SIZE):
    _row = _i // INV_GRID_COLS
    _col = _i % INV_GRID_COLS
    _x = INV_GRID_X + _col * (INV_SLOT_SIZE + INV_SLOT_GAP)
    _y = INV_GRID_TOP_Y - _row * (INV_SLOT_SIZE + INV_SLOT_GAP) - INV_SLOT_SIZE
    inventory_slot_boxes.append(
        shapes.BorderedRectangle(
            _x, _y, INV_SLOT_SIZE, INV_SLOT_SIZE,
            border=2,
            color=(30, 30, 38),
            border_color=(90, 90, 100),
            batch=inventory_batch,
            group=inventory_shape_group,
        )
    )

_inventory_item_sprites = [None] * INVENTORY_SIZE
selected_inventory_slot = None

inventory_detail_name = pyglet.text.Label(
    "",
    font_size=16,
    weight="bold",
    x=WINDOW_WIDTH / 2,
    y=190,
    anchor_x="center",
    anchor_y="center",
    color=(255, 230, 140, 255),
    batch=inventory_batch,
    group=inventory_text_group,
)
inventory_detail_desc = pyglet.text.Label(
    "Selectionne un objet dans la grille.",
    font_size=12,
    x=WINDOW_WIDTH / 2,
    y=155,
    width=560,
    multiline=True,
    align="center",
    anchor_x="center",
    anchor_y="center",
    color=(210, 210, 210, 255),
    batch=inventory_batch,
    group=inventory_text_group,
)

inventory_equip_button = Button(
    WINDOW_WIDTH / 2 - 230, 60, 220, 40, "Equiper",
    inventory_batch, inventory_shape_group, inventory_text_group, font_size=13,
)
inventory_sell_button = Button(
    WINDOW_WIDTH / 2 + 10, 60, 220, 40, "Vendre",
    inventory_batch, inventory_shape_group, inventory_text_group, font_size=13,
)


def refresh_inventory_view():
    inventory = PLAYER_INVENTORY[current_player]

    for i in range(INVENTORY_SIZE):
        if _inventory_item_sprites[i] is not None:
            _inventory_item_sprites[i].delete()
            _inventory_item_sprites[i] = None

        box = inventory_slot_boxes[i]
        item_key = inventory[i]
        if item_key is not None:
            image = get_card_image(*item_key)
            if image is not None:
                sprite = pyglet.sprite.Sprite(
                    image, x=box.x + 5, y=box.y + 5,
                    batch=inventory_batch, group=inventory_shape_group,
                )
                sprite.scale_x = (INV_SLOT_SIZE - 10) / image.width
                sprite.scale_y = (INV_SLOT_SIZE - 10) / image.height
                _inventory_item_sprites[i] = sprite

        box.border_color = (255, 220, 100) if i == selected_inventory_slot else (90, 90, 100)

    item_key = (
        inventory[selected_inventory_slot] if selected_inventory_slot is not None else None
    )
    if item_key is not None:
        item = ITEMS[item_key]
        inventory_detail_name.text = item["name"]
        inventory_detail_desc.text = item["description"]
        inventory_equip_button.label.text = "Equiper (choisir un heros)"
        inventory_sell_button.label.text = f"Vendre (+{item.get('sell_value', 0)} or)"
    else:
        inventory_detail_name.text = ""
        inventory_detail_desc.text = "Selectionne un objet dans la grille."
        inventory_equip_button.label.text = "Equiper"
        inventory_sell_button.label.text = "Vendre"


# --- Etats de l'application ---------------------------------------------

STATE_MENU = "menu"
STATE_GAME = "game"
STATE_INDEX = "index"
STATE_INVENTORY = "inventory"
state = STATE_MENU


@window.event
def on_draw():
    window.clear()
    if state == STATE_MENU:
        menu_batch.draw()
    elif state == STATE_GAME:
        batch.draw()
    elif state == STATE_INDEX:
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glScissor(
            0,
            INDEX_CONTENT_BOTTOM,
            WINDOW_WIDTH,
            INDEX_CONTENT_TOP - INDEX_CONTENT_BOTTOM,
        )
        index_content_batch.draw()
        gl.glDisable(gl.GL_SCISSOR_TEST)
        index_batch.draw()
    elif state == STATE_INVENTORY:
        inventory_batch.draw()


@window.event
def on_mouse_press(x, y, button, modifiers):
    global selected_card, drag_dx, drag_dy, state
    global selected_inventory_slot, pending_equip_item
    if button != mouse.LEFT:
        return

    if state == STATE_MENU:
        if play_button.contains(x, y):
            start_new_game()
            state = STATE_GAME
        elif index_button.contains(x, y):
            if index_mode != "heroes":
                switch_index_mode()
            else:
                scroll_index(-index_scroll_offset)  # revient en haut de l'index
            state = STATE_INDEX
        return

    if state == STATE_INDEX:
        if back_button.contains(x, y):
            state = STATE_MENU
        elif index_tab_button.contains(x, y):
            switch_index_mode()
        return

    if state == STATE_INVENTORY:
        if inventory_back_button.contains(x, y):
            state = STATE_GAME
            return
        for i, box in enumerate(inventory_slot_boxes):
            if rect_contains(box.x, box.y, INV_SLOT_SIZE, INV_SLOT_SIZE, x, y):
                selected_inventory_slot = i
                refresh_inventory_view()
                return
        if inventory_equip_button.contains(x, y):
            if (
                selected_inventory_slot is not None
                and PLAYER_INVENTORY[current_player][selected_inventory_slot] is not None
            ):
                pending_equip_item = (current_player, selected_inventory_slot)
                state = STATE_GAME
            return
        if inventory_sell_button.contains(x, y):
            if selected_inventory_slot is not None:
                sell_item(current_player, selected_inventory_slot)
                refresh_inventory_view()
            return
        return

    if pending_equip_item is not None:
        pending_player, pending_slot = pending_equip_item
        item_key = PLAYER_INVENTORY[pending_player][pending_slot]
        if item_key is None or pending_player != current_player:
            pending_equip_item = None
        else:
            side_rows = PLAYER_SIDE_ROWS[current_player]
            for card in reversed(cards):
                if (
                    card.building is None
                    and card.row in side_rows
                    and card.equipped_item is None
                    and card.contains_point(x, y)
                ):
                    equip_item_on_card(card, item_key)
                    PLAYER_INVENTORY[pending_player][pending_slot] = None
                    pending_equip_item = None
                    update_turn_ui()
                    return
            return

    if pass_button.contains(x, y):
        pass_turn()
        return

    if recruit_button.contains(x, y):
        recruit_hero()
        return

    if inventory_button.contains(x, y):
        pending_equip_item = None
        selected_inventory_slot = None
        refresh_inventory_view()
        state = STATE_INVENTORY
        return

    if mine_upgrade_button.contains(x, y):
        upgrade_building("mine")
        return

    if camp_upgrade_button.contains(x, y):
        upgrade_building("camp")
        return

    side_rows = PLAYER_SIDE_ROWS[current_player]
    assigned_cards = [
        c for c in MINE_ASSIGNMENTS[current_player] + CAMP_ASSIGNMENTS[current_player]
        if c is not None
    ]
    selectable = list(reversed(cards))
    for card in selectable:
        if card in assigned_cards and card.contains_point(x, y):
            selected_card = card
            drag_dx = x - card.x
            drag_dy = y - card.y
            return
    for card in selectable:
        if card.building is None and card.row in side_rows and card.contains_point(x, y):
            selected_card = card
            drag_dx = x - card.x
            drag_dy = y - card.y
            break


@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if state == STATE_GAME and selected_card is not None:
        selected_card.set_position_px(x - drag_dx, y - drag_dy)


@window.event
def on_mouse_scroll(x, y, scroll_x, scroll_y):
    if state == STATE_INDEX:
        scroll_index(-scroll_y * INDEX_SCROLL_SPEED)


def revert_selected_card(card, came_from_building):
    if came_from_building is not None:
        position_in_building(card, came_from_building, card.building_slot)
    else:
        card.snap_to_cell(card.row, card.col)


def try_assign_building(card, building, came_from_building):
    player = current_player
    slots = MINE_ASSIGNMENTS[player] if building == "mine" else CAMP_ASSIGNMENTS[player]
    capacity = (MINE_CAPACITY if building == "mine" else CAMP_CAPACITY)[player]
    same_building = came_from_building == building

    target_index = None
    for i in range(capacity):
        if slots[i] is None or slots[i] is card:
            target_index = i
            break

    if target_index is None:
        revert_selected_card(card, came_from_building)
        return

    if not same_building and PLAYER_MOVEMENT[player] < MOVE_COST:
        revert_selected_card(card, came_from_building)
        return

    if came_from_building is not None:
        other_slots = (
            MINE_ASSIGNMENTS[player] if came_from_building == "mine" else CAMP_ASSIGNMENTS[player]
        )
        if card.building_slot is not None and other_slots[card.building_slot] is card:
            other_slots[card.building_slot] = None
    else:
        pos = (card.row, card.col)
        if occupied.get(pos) is card:
            del occupied[pos]

    card.building = building
    card.building_slot = target_index
    slots[target_index] = card
    position_in_building(card, building, target_index)

    if not same_building:
        PLAYER_MOVEMENT[player] -= MOVE_COST
    update_turn_ui()


@window.event
def on_mouse_release(x, y, button, modifiers):
    global selected_card
    if state != STATE_GAME or selected_card is None:
        return

    card = selected_card
    came_from_building = card.building
    center_x = card.x + card.width / 2
    center_y = card.y + card.height / 2

    if rect_contains(*building_zone_rect("mine"), center_x, center_y):
        try_assign_building(card, "mine", came_from_building)
        selected_card = None
        return

    if rect_contains(*building_zone_rect("camp"), center_x, center_y):
        try_assign_building(card, "camp", came_from_building)
        selected_card = None
        return

    side_rows = PLAYER_SIDE_ROWS[current_player]
    row, col = pixel_to_cell(center_x, center_y)

    if row not in side_rows:
        # Hors de son propre cote : coup invalide.
        revert_selected_card(card, came_from_building)
        selected_card = None
        return

    target = occupied.get((row, col))

    if target is None or target is card:
        moved = came_from_building is not None or (row, col) != (card.row, card.col)
        if moved and PLAYER_MOVEMENT[current_player] >= MOVE_COST:
            if came_from_building is not None:
                slots = (
                    MINE_ASSIGNMENTS if came_from_building == "mine" else CAMP_ASSIGNMENTS
                )[current_player]
                if card.building_slot is not None and slots[card.building_slot] is card:
                    slots[card.building_slot] = None
                card.building = None
                card.building_slot = None
            else:
                del occupied[(card.row, card.col)]
            card.snap_to_cell(row, col)
            occupied[(row, col)] = card
            PLAYER_MOVEMENT[current_player] -= MOVE_COST
            update_turn_ui()
        else:
            revert_selected_card(card, came_from_building)
    elif came_from_building is not None:
        # Une carte assignee a un batiment doit d'abord revenir sur le
        # plateau avant de pouvoir fusionner.
        revert_selected_card(card, came_from_building)
    else:
        result = merge_result(
            (card.tier, card.number), (target.tier, target.number)
        )
        if (
            result is not None
            and card.is_charged()
            and target.is_charged()
            and PLAYER_MOVEMENT[current_player] >= FUSE_COST
        ):
            result_tier, result_number = result
            del occupied[(card.row, card.col)]
            cards.remove(card)
            cards.remove(target)
            card.delete()
            target.delete()
            merged = Card(row, col, result_tier, result_number)
            cards.append(merged)
            occupied[(row, col)] = merged
            PLAYER_MOVEMENT[current_player] -= FUSE_COST
            update_turn_ui()
        else:
            revert_selected_card(card, came_from_building)

    selected_card = None


if __name__ == "__main__":
    pyglet.app.run()
