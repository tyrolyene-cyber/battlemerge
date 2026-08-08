"""
Objets (reliques) lachees par les heros a leur mort.

Cle : (tier, numero) du heros qui correspond a la relique (celui
qui la lache en mourant). Valeur : dict avec
    - "name"           : nom affiche
    - "description"    : texte affiche dans l'index
    - "hp_bonus"       : bonus de vie de base, permanent, une fois equipe
    - "atk_bonus"      : bonus d'attaque de base, permanent, une fois equipe
    - "passive_boost"  : bonus en % applique a la valeur de la capacite
                        de classe, MAIS seulement si l'objet est
                        equipe sur le heros dont il porte le nom
                        (meme tier et numero)
    - "sell_value"     : or obtenu en le vendant
"""

ITEMS = {
    # Tier 1
    (1, 1): {
        "name": "Longue-vue de l'Eclaireur",
        "description": '+8 PV, +2 ATQ. Sur un Eclaireur, booste sa capacite de classe de +30%.',
        "hp_bonus": 8,
        "atk_bonus": 2,
        "passive_boost": 0.3,
        "sell_value": 40,
    },
    (1, 2): {
        "name": 'Dague du Voleur',
        "description": '+8 PV, +2 ATQ. Sur un Voleur, booste sa capacite de classe de +30%.',
        "hp_bonus": 8,
        "atk_bonus": 2,
        "passive_boost": 0.3,
        "sell_value": 40,
    },
    (1, 3): {
        "name": "Carquois de l'Archer",
        "description": '+8 PV, +2 ATQ. Sur un Archer, booste sa capacite de classe de +30%.',
        "hp_bonus": 8,
        "atk_bonus": 2,
        "passive_boost": 0.3,
        "sell_value": 40,
    },
    (1, 4): {
        "name": 'Epee du Guerrier',
        "description": '+8 PV, +2 ATQ. Sur un Guerrier, booste sa capacite de classe de +30%.',
        "hp_bonus": 8,
        "atk_bonus": 2,
        "passive_boost": 0.3,
        "sell_value": 40,
    },
    (1, 5): {
        "name": 'Fiole du Soigneur',
        "description": '+8 PV, +2 ATQ. Sur un Soigneur, booste sa capacite de classe de +30%.',
        "hp_bonus": 8,
        "atk_bonus": 2,
        "passive_boost": 0.3,
        "sell_value": 40,
    },
    # Tier 2
    (2, 1): {
        "name": 'Grimoire du Mage',
        "description": '+14 PV, +4 ATQ. Sur un Mage, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    (2, 2): {
        "name": 'Bouclier du Tank',
        "description": '+14 PV, +4 ATQ. Sur un Tank, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    (2, 3): {
        "name": "Poison de l'Assassin",
        "description": '+14 PV, +4 ATQ. Sur un Assassin, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    (2, 4): {
        "name": 'Hache du Berserker',
        "description": '+14 PV, +4 ATQ. Sur un Berserker, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    (2, 5): {
        "name": 'Amulette du Paladin',
        "description": '+14 PV, +4 ATQ. Sur un Paladin, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    (2, 6): {
        "name": "Totem de l'Invocateur",
        "description": '+14 PV, +4 ATQ. Sur un Invocateur, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    (2, 7): {
        "name": "Fiole de l'Alchimiste",
        "description": '+14 PV, +4 ATQ. Sur un Alchimiste, booste sa capacite de classe de +30%.',
        "hp_bonus": 14,
        "atk_bonus": 4,
        "passive_boost": 0.3,
        "sell_value": 70,
    },
    # Tier 3
    (3, 1): {
        "name": 'Luth du Barde',
        "description": '+20 PV, +6 ATQ. Sur un Barde, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 2): {
        "name": 'Lance du Chevalier',
        "description": '+20 PV, +6 ATQ. Sur un Chevalier, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 3): {
        "name": 'Grimoire du Necromancien',
        "description": '+20 PV, +6 ATQ. Sur un Necromancien, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 4): {
        "name": 'Feuille du Druide',
        "description": '+20 PV, +6 ATQ. Sur un Druide, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 5): {
        "name": 'Bandages du Moine',
        "description": '+20 PV, +6 ATQ. Sur un Moine, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 6): {
        "name": 'Piege du Chasseur',
        "description": '+20 PV, +6 ATQ. Sur un Chasseur, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 7): {
        "name": 'Ecu du Gardien',
        "description": '+20 PV, +6 ATQ. Sur un Gardien, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
    (3, 8): {
        "name": 'Grimoire noir du Sorcier',
        "description": '+20 PV, +6 ATQ. Sur un Sorcier, booste sa capacite de classe de +30%.',
        "hp_bonus": 20,
        "atk_bonus": 6,
        "passive_boost": 0.3,
        "sell_value": 110,
    },
}
