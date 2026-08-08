"""
Table des fusions.

Chaque heros est identifie par (tier, numero), ce qui correspond au
nom de son image dans assets/cards/ (ex: (1, 1) -> "1.1.png").

Chaque entree dit : quand CES DEUX heros precis fusionnent ensemble,
quel heros on obtient. L'ordre des deux heros dans la paire n'a pas
d'importance : (1, 1) + (1, 2) == (1, 2) + (1, 1).

Format :
    (heros_a, heros_b): heros_resultat

Toutes les combinaisons possibles entre heros d'un meme tier sont
generees automatiquement (resultat tire au hasard une fois, puis fixe
ici) des qu'un tier superieur existe. Change une valeur ici pour
forcer un resultat precis pour une combinaison donnee.

Si une combinaison n'est pas listee ici (ex: le tier le plus haut,
qui n'a pas de tier superieur), la fusion est refusee et les deux
cartes reviennent a leur place.
"""

FUSIONS = {
    # Tier 1
    ((1, 1), (1, 1)): (2, 1),
    ((1, 1), (1, 2)): (2, 2),
    ((1, 1), (1, 3)): (2, 2),
    ((1, 1), (1, 4)): (2, 1),
    ((1, 1), (1, 5)): (2, 4),
    ((1, 2), (1, 2)): (2, 3),
    ((1, 2), (1, 3)): (2, 1),
    ((1, 2), (1, 4)): (2, 6),
    ((1, 2), (1, 5)): (2, 7),
    ((1, 3), (1, 3)): (2, 3),
    ((1, 3), (1, 4)): (2, 1),
    ((1, 3), (1, 5)): (2, 6),
    ((1, 4), (1, 4)): (2, 6),
    ((1, 4), (1, 5)): (2, 2),
    ((1, 5), (1, 5)): (2, 5),
    # Tier 2
    ((2, 1), (2, 1)): (3, 1),
    ((2, 1), (2, 2)): (3, 2),
    ((2, 1), (2, 3)): (3, 1),
    ((2, 1), (2, 4)): (3, 5),
    ((2, 1), (2, 5)): (3, 5),
    ((2, 1), (2, 6)): (3, 5),
    ((2, 1), (2, 7)): (3, 5),
    ((2, 2), (2, 2)): (3, 2),
    ((2, 2), (2, 3)): (3, 1),
    ((2, 2), (2, 4)): (3, 7),
    ((2, 2), (2, 5)): (3, 5),
    ((2, 2), (2, 6)): (3, 7),
    ((2, 2), (2, 7)): (3, 3),
    ((2, 3), (2, 3)): (3, 2),
    ((2, 3), (2, 4)): (3, 4),
    ((2, 3), (2, 5)): (3, 4),
    ((2, 3), (2, 6)): (3, 4),
    ((2, 3), (2, 7)): (3, 3),
    ((2, 4), (2, 4)): (3, 7),
    ((2, 4), (2, 5)): (3, 8),
    ((2, 4), (2, 6)): (3, 7),
    ((2, 4), (2, 7)): (3, 7),
    ((2, 5), (2, 5)): (3, 2),
    ((2, 5), (2, 6)): (3, 3),
    ((2, 5), (2, 7)): (3, 1),
    ((2, 6), (2, 6)): (3, 7),
    ((2, 6), (2, 7)): (3, 1),
    ((2, 7), (2, 7)): (3, 8),
}
