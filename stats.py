"""
Statistiques des heros : vie (points de vie) et attaque.

Cle : (tier, numero), comme dans fusions.py.
Valeur : (vie, attaque).

Plus le tier est eleve, plus les stats sont fortes. Ces valeurs
sont ecrites en dur ici : modifie-les directement pour ajuster
l'equilibrage, rien n'est recalcule automatiquement.
"""

STATS = {
    # Tier 1
    (1, 1): (94, 10),
    (1, 2): (52, 15),
    (1, 3): (78, 12),
    (1, 4): (68, 9),
    (1, 5): (70, 13),
    # Tier 2
    (2, 1): (147, 29),
    (2, 2): (178, 25),
    (2, 3): (181, 20),
    (2, 4): (186, 27),
    (2, 5): (171, 23),
    (2, 6): (147, 21),
    (2, 7): (162, 23),
    # Tier 3
    (3, 1): (251, 42),
    (3, 2): (228, 40),
    (3, 3): (267, 41),
    (3, 4): (263, 43),
    (3, 5): (241, 42),
    (3, 6): (226, 42),
    (3, 7): (259, 39),
    (3, 8): (262, 39),
}
