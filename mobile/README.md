# BattleMerge — version mobile (iPhone)

Portage jouable au doigt de `main.py` en application web (HTML/CSS/JS
vanilla, sans dépendance ni étape de build). Un iPhone ne peut pas lancer
directement le prototype pyglet (Python de bureau) ; cette version web est
le moyen le plus direct de le rendre jouable sur iPhone : elle s'ouvre dans
Safari et peut être ajoutée à l'écran d'accueil comme une vraie app
(PWA), plein écran, avec icône et sans barre d'adresse.

## Jouer en local (test rapide)

Depuis la racine du dépôt :

```bash
cd mobile
python3 -m http.server 8000
```

Puis ouvre `http://<ip-de-ton-ordinateur>:8000` depuis Safari sur
l'iPhone (même réseau Wi-Fi).

## Jouer sur iPhone via internet (recommandé) : GitHub Pages

1. Sur GitHub : **Settings → Pages**.
2. Source : *Deploy from a branch*, branche `main` (ou celle mergée),
   dossier `/mobile`... si l'option "dossier personnalisé" n'est pas
   proposée, choisis `/ (root)` avec la branche `gh-pages` générée par
   une action, ou déplace simplement le contenu de `mobile/` vers
   `docs/` à la racine et sélectionne `/docs`.
3. Une fois publié, ouvre l'URL fournie (ex.
   `https://<utilisateur>.github.io/battlemerge/`) dans Safari sur
   l'iPhone.
4. Bouton **Partager** → **Sur l'écran d'accueil**. L'app s'installe
   avec sa propre icône et s'ouvre en plein écran, sans interface
   Safari.

## Contenu

- `index.html`, `styles.css`, `app.js` — l'application (menu, plateau,
  index des héros).
- `data.js` — **généré automatiquement** à partir de `fusions.py` et
  `stats.py` du prototype desktop (voir script utilisé lors du
  portage). Si tu modifies les stats ou les fusions côté Python,
  régénère ce fichier pour les répercuter côté mobile.
- `assets/` — copie des visuels de `assets/`, renommés avec la bonne
  extension (`.webp`/`.avif`/`.jpg`/`.png` détectée par contenu réel du
  fichier, car plusieurs fichiers du dossier source portent une
  extension `.png` trompeuse).
- `manifest.webmanifest`, `sw.js`, `icons/` — rendent l'app installable
  (PWA) et jouable hors-ligne une fois ouverte une première fois.

## Différences avec le prototype desktop

- **Contrôles tactiles** : glisser-déposer au doigt (Pointer Events)
  au lieu de la souris.
- **Mise en page portrait** : la grille 4×6 s'adapte à l'écran de
  l'iPhone (pas besoin de tourner le téléphone).
- **Écran de fin de partie ajouté** : le prototype Python n'a pas de
  condition de victoire ; la version mobile déclare vainqueur le
  joueur qui a encore des héros sur le plateau après un round de
  combat, pour offrir une partie jouable de bout en bout.
- Tout le reste (fusions, jauge de charge, résolution des combats,
  ordre d'attaque) reproduit fidèlement `main.py`.

## Vers une vraie app iOS (App Store)

Ce dossier est une PWA, pas un binaire iOS natif — ce container n'a
pas d'Xcode/macOS pour compiler un `.ipa`. Deux pistes pour aller plus
loin, si besoin :

- **Rester en PWA** (ce qui est livré ici) : gratuit, pas de compte
  développeur, installation instantanée par lien.
- **Empaqueter en app native** avec [Capacitor](https://capacitorjs.com/)
  autour de ce même dossier `mobile/` : nécessite un Mac avec Xcode et
  un compte Apple Developer (99 $/an) pour publier sur l'App Store.
