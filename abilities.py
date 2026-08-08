"""
Capacite de chaque classe (specialite), avec un vrai effet en jeu.

Cle : nom de la specialite, tel qu'utilise dans specialties.py.
Valeur : dict avec
    - "description" : texte affiche dans l'index.
    - "effect"      : identifiant lu par main.py pour appliquer l'effet.
    - "value"       : parametre numerique de l'effet (ratio, montant...).

Modifie "value" pour ajuster l'equilibrage sans toucher au code du jeu.
Les effets geres par main.py sont :
    bonus_vs_full_hp  +value en % de degats si la cible est a PV max
    gold_steal        vole "value" or a l'adversaire par coup porte
    target_weakest    vise toujours l'ennemi avec le moins de PV
    bonus_damage      +value en % de degats infliges
    heal_ally         soigne l'allie le plus blesse au lieu d'attaquer
    cleave            inflige aussi value% dans les degats a un 2e ennemi
    taunt             force l'ennemi a l'attaquer en priorite
    execute           +value en % de degats si la cible est sous 50% PV
    rage              +value en % de degats selon les PV manquants
    damage_shield     ses allies de la ligne prennent value% de degats en moins
    fast_charge       double sa propre jauge de charge gagnee
    self_growth       gagne un petit bonus de PV/attaque permanent par round
    rally             ses allies de la ligne gagnent de la jauge en plus
    overkill          les degats en trop apres un kill touchent un autre ennemi
    revive            chance de ranimer un allie de sa ligne tombe au combat
    dodge             chance d'esquiver totalement une attaque
    double_attack     attaque deux fois par round
    weaken            reduit l'attaque de sa cible de value% par coup porte
"""

CLASS_ABILITIES = {
    "Eclaireur": {
        "description": "Inflige +50% de degats si la cible est a pleine vie.",
        "effect": "bonus_vs_full_hp",
        "value": 0.5,
    },
    "Voleur": {
        "description": "Vole 20 or a l'adversaire a chaque coup porte.",
        "effect": "gold_steal",
        "value": 20,
    },
    "Archer": {
        "description": "Vise toujours l'ennemi ayant le moins de PV.",
        "effect": "target_weakest",
        "value": 0,
    },
    "Guerrier": {
        "description": "Inflige 25% de degats supplementaires.",
        "effect": "bonus_damage",
        "value": 0.25,
    },
    "Soigneur": {
        "description": "Soigne l'allie le plus blesse de sa ligne au lieu d'attaquer.",
        "effect": "heal_ally",
        "value": 0.25,
    },
    "Mage": {
        "description": "Inflige aussi 50% de ses degats a un second ennemi au hasard.",
        "effect": "cleave",
        "value": 0.5,
    },
    "Tank": {
        "description": "Attire toujours les attaques ennemies pour proteger ses allies.",
        "effect": "taunt",
        "value": 0,
    },
    "Assassin": {
        "description": "Inflige +75% de degats a une cible sous 50% de ses PV.",
        "effect": "execute",
        "value": 0.75,
    },
    "Berserker": {
        "description": "Plus il est blesse, plus son attaque augmente (jusqu'a +100%).",
        "effect": "rage",
        "value": 1.0,
    },
    "Paladin": {
        "description": "Ses allies de la ligne prennent 20% de degats en moins.",
        "effect": "damage_shield",
        "value": 0.2,
    },
    "Invocateur": {
        "description": "Gagne deux fois plus de jauge de charge en combat.",
        "effect": "fast_charge",
        "value": 0,
    },
    "Alchimiste": {
        "description": "Gagne un petit bonus de PV et d'attaque permanent chaque round.",
        "effect": "self_growth",
        "value": 0,
    },
    "Barde": {
        "description": "Ses allies de la ligne gagnent de la jauge en plus chaque round.",
        "effect": "rally",
        "value": 0,
    },
    "Chevalier": {
        "description": "Les degats en trop apres avoir tue sa cible touchent un autre ennemi.",
        "effect": "overkill",
        "value": 0,
    },
    "Necromancien": {
        "description": "Chance de ranimer un allie de sa ligne tombe au combat.",
        "effect": "revive",
        "value": 0.3,
    },
    "Druide": {
        "description": "A une chance d'esquiver totalement une attaque.",
        "effect": "dodge",
        "value": 0.25,
    },
    "Moine": {
        "description": "Attaque deux fois a chaque round.",
        "effect": "double_attack",
        "value": 0,
    },
    "Chasseur": {
        "description": "Reduit l'attaque de sa cible de 20% a chaque coup porte.",
        "effect": "weaken",
        "value": 0.2,
    },
    "Gardien": {
        "description": "Attire toujours les attaques ennemies pour proteger ses allies.",
        "effect": "taunt",
        "value": 0,
    },
    "Sorcier": {
        "description": "Reduit l'attaque de sa cible de 30% a chaque coup porte.",
        "effect": "weaken",
        "value": 0.3,
    },
}
