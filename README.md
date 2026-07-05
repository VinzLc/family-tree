# Arbre généalogique Jastrzębski · Leclercq

Site d'une page, style parchemin, **piloté par les données**.

## Fichiers

| Fichier | Rôle |
|---|---|
| `genealogie.json` | **La donnée** — personnes, unions, sources, pistes de recherche. C'est le seul fichier à éditer à la main. |
| `build.py` | Générateur : lit le JSON et (re)produit `index.html`. |
| `index.html` | **Généré** — ne pas éditer à la main (sera écrasé au prochain build). |
| `img/` | Images dérivées affichées dans la page (portraits recadrés, photos de l'album redimensionnées). |
| `sources/` | Scans d'origine (actes, passeports, cartes d'identité, photos). Jamais affichés bruts. |

## Workflow

```bash
# 1. éditer la donnée
$EDITOR genealogie.json
# 2. régénérer la page
python3 build.py
# 3. ouvrir index.html (double-clic) — ou pour un rendu/QA :
#    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
#      --headless=new --screenshot=render.png --window-size=1320,3300 \
#      file://$PWD/index.html
```

## Ajouter une personne

1. Ajouter un objet dans `people[]` (id préfixé `p_`, `names`, `sex`, `parents.unionId`, `events`).
2. La relier : soit comme partenaire d'une `unions[]`, soit comme enfant (`children`) d'une union, soit en créant une nouvelle union (id préfixé `u_`).
3. (Optionnel) un bloc `display` contrôle l'affichage de la carte ; sinon le build déduit `meta`/`role`/`src` depuis les `events`.

```jsonc
"display": {
  "confidence": "documented",   // documented | probable | inferred | family | unknown  -> style de la carte
  "role": "Père de X",          // petite ligne en capitales
  "meta": "né le <span class=\"yr\">…</span><br>…",  // HTML libre (sinon auto depuis events)
  "src":  "Acte …"              // mention de source (sinon auto depuis events.sources)
}
"portrait": { "file": "img/x.jpg", "alt": "…", "source": "s_…" }   // vignette sur la carte
```

L'arbre se construit en remontant depuis `meta.rendering.rootUnionId` (l'union des parents de la personne de référence). Marquer une union avec `display.focal: true` lui donne le style « pivot » + un bandeau de mariage (`display.marriageTag`).

Les libellés de génération s'étendent automatiquement : *Parents → Grands-parents → Arrière-grands-parents*, puis les termes d'ascendance (`AIEUL_TERMS` dans `build.py`) **Trisaïeuls, Quadrisaïeuls, … Décaïeuls** suivis du n° de génération. La lignée paternelle Leclercq remonte aujourd'hui jusqu'à **Harnes (v. 1640)**, documentée par les actes paroissiaux de 1696, 1710 et 1770.

**Fiche détaillée d'une personne :** survoler une carte l'agrandit légèrement ; cliquer (ou Entrée au clavier) ouvre une **popup** détaillée (repères de vie, famille = parents / conjoint·e / enfants, notes, et sources cliquables). Les données par personne sont générées dans `person_detail()` → objet JS `FAPEOPLE` ; le rendu se fait côté client (`person_modal_html()`).

**Familles alliées (masquées par défaut) :** l'arbre est centré sur les lignées **Leclercq** et **Jastrzębski**. L'ascendance des épouses (Lesire, Léonard, Dufour, Detournay, Waflart, Devillers, Bauduin…, reprise de `sources/Arbre.pdf` / Filae) est marquée `"tier": "extended"` sur les unions et personnes concernées ; les stacks `.ext` sont **cachés par défaut** (`.stack.ext{display:none}`). Deux façons de révéler : un **petit bouton discret par génération** (`.gen-ext-btn` → bascule `.show-ext` sur la ligne `.ancestors` voisine) et le **bouton global en bas de l'arbre** (« Afficher toutes les familles alliées » → bascule `.show-all` sur `.tree`). Les personnes `extended` sont exclues de la carte. Pour rattacher une nouvelle branche alliée : ajouter personnes/unions avec `"tier":"extended"` et lier l'épouse déjà présente via `parents.unionId`.

**Frères (collatéraux) :** les enfants masculins d'une union qui ne sont pas eux-mêmes des ancêtres (donc absents de `partner_ids`) sont affichés en **petites cartes « frère »** sous le couple (`sibling_card()`), cliquables comme les autres. C'est ainsi qu'apparaît p. ex. Pierre Joseph Leclercq (1891-1914, mort pour la France), frère de Jules. Pour ajouter un frère : l'ajouter dans `children` de l'union parentale sans le marier (il ne devient pas partenaire d'une union).

**Empilement (z-index) :** carte Leaflet ~1000 < fiche personne (2500) < carte plein écran (2000) / lightbox images (3000). Toute nouvelle surcouche doit passer au-dessus de Leaflet (> 1000).

## Carte des lieux

Une carte interactive (Leaflet + tuiles OpenStreetMap) sous l'album agrège les événements par lieu. Les lieux vivent dans `places` du JSON :

```jsonc
"places": {
  "noyelles": { "name": "Noyelles-sous-Lens", "detail": "Pas-de-Calais (France)",
                "lat": 50.4197, "lon": 2.8989, "aliases": ["Noyelles-sous-Lens", "Noyelles"] }
}
```

`build.py` rattache chaque `event.place` à un lieu via ses `aliases` (sous-chaîne), puis pose un marqueur : **survol** = infobulle listant les événements (avec années), **clic** = popup. Les tuiles sont celles d'**OpenStreetMap France** (libellés en français). La route de migration est dans `meta.rendering.migration` (paires de clés de lieux) ; `build.py` calcule la **distance (haversine)** de chaque segment et l'affiche sur la ligne. Le bouton **⛶** (sous les contrôles de zoom) bascule la carte en **plein écran** dans une popup (fermeture : ×, Échap, ou clic sur le fond). Ajouter un lieu = une entrée dans `places` + des `aliases` qui matchent le texte des `events`.

> Dépendances en ligne : Google Fonts, et pour la carte Leaflet + tuiles OSM France (la page a besoin d'Internet pour le rendu complet ; le reste fonctionne hors-ligne).

## Convention de confiance

`documented` (acte) · `probable` (index Geneteka) · `inferred` (déduit) · `family` (mémoire familiale) · `unknown` (à retrouver).

## Sources consultables

Chaque `sources[]` peut porter un champ `file` (chemin vers le scan dans `sources/`, ou une URL — ex. l'index Geneteka en ligne). Le panneau « Sources utilisées » transforme alors le titre en lien :

- **Scan image** (`.jpg/.jpeg/.png/.gif/.webp`) → indicateur **⌕**, s'ouvre dans la **popup** (même lightbox que l'album) avec un bouton **Télécharger**. Les chemins sont URL-encodés au build (`quote`), donc les noms de fichiers avec espaces/accents fonctionnent.
- **URL externe** ou **PDF** (ex. l'arbre Filae) → indicateur **↗**, s'ouvre dans un **nouvel onglet**.

> Les scans bruts vivent dans `sources/` mais ne sont jamais montrés en pleine page sans clic. Un document trop récent / privé (ex. une carte d'identité contemporaine) ne doit pas être référencé dans `sources[]` ni utilisé comme `portrait`.
