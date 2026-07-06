---
name: ingest-documents
description: >
  Runbook pour intégrer de nouveaux documents généalogiques (scans d'actes,
  recensements, fiches matricules, articles) déposés dans sources/ vers
  genealogie.json puis index.html. À utiliser dès que l'utilisateur dit qu'il a
  ajouté / partagé des documents « dans le dossier », qu'il y a « N nouveaux
  documents à traiter », ou demande d'« étoffer l'arbre » à partir de scans.
  Couvre : repérage des nouveaux fichiers, lecture OCR des manuscrits par
  recadrage-zoom, recoupement avec les données existantes, saisie selon les
  conventions du projet, et boucle rebuild + QA. Complète CLAUDE.md (qui décrit
  l'architecture) par la procédure pas-à-pas.
---

# Traiter un lot de documents

`CLAUDE.md` décrit **l'architecture** (schéma, `CONF_CLASS`, tier `extended`,
collatéraux, hauteur uniforme des cartes, `sources/` vs `img/`, z-index…).
Lis-le d'abord. Ce skill est le **runbook** : les étapes quand un lot arrive.

## 0. Outillage (déjà en place)

Ce Mac n'a ni ImageMagick ni Pillow système. Un venv persistant existe :
`tools/venv`. S'il manque, le recréer une fois :

```bash
python3 -m venv tools/venv && tools/venv/bin/pip install -q Pillow
```

Ne **jamais** recréer un venv jetable dans `/tmp` — utiliser `tools/crop.py`.

## 1. Repérer les nouveaux fichiers

```bash
ls -lat sources/ | head -15                 # les plus récents en haut
grep -o '"file": "sources/[^"]*"' genealogie.json | sort -u   # déjà référencés
```

Un fichier récent **déjà** dans `sources[]` (mêmes faits) est un doublon → ne
pas le ré-ajouter (ex. une 2ᵉ photo d'une fiche matricule déjà citée). Le compte
annoncé par l'utilisateur exclut souvent ces quasi-doublons ; réconcilie.

## 2. Lire les manuscrits (OCR par zoom)

Toujours : voir la taille, puis recadrer la zone utile en pixels de l'original,
agrandir, et **Read** le PNG produit.

```bash
tools/venv/bin/python tools/crop.py "sources/Recensement1921...jpg"          # taille
tools/venv/bin/python tools/crop.py "sources/…jpg" --box 150 2000 2380 2680 --scale 2
tools/venv/bin/python tools/crop.py "sources/…jpg" --box 2560 1600 2860 3200 --rotate -90  # nom de rue en marge
```

Aides de lecture pour les registres du Pas-de-Calais / Oise :

- **Recensement** : colonnes *Noms · Prénoms · Année de naissance · Lieu ·
  Situation (chef/épouse/fils/fille/beau-fils) · Profession*. Un **n° de ménage**
  regroupe un foyer. « **beau-fils/belle-fille** » = gendre/bru. Un enfant « **2
  mois** » **date la naissance** dans l'année du recensement. Croise l'**âge** →
  année de naissance (± 1).
- **Fiche matricule** : n° de canton (liste) ≠ n° au répertoire (matricule).
  Corps d'affectation, décisions, « détail des services » (dates, décès).
- **Table des successions** : profession, âge, domicile, lieu de décès, état
  (célibataire/veuf), **filiation** (« fils de … et … »).

## 3. Recouper avant de saisir

Pour chaque personne/lieu/fait, se demander : **existe déjà ?**

```bash
grep -n 'p_jules_lesire\|u_juleslesire_clemence' genealogie.json
```

- Fait déjà présent en `probable`/`family` et le scan le prouve → **remonter la
  confidence** à `documented` et **ajouter la source** (ne pas dupliquer la
  personne). Garder une note expliquant la corroboration.
- Personne/union inconnue → créer (voir gabarits §4).
- Ne **jamais** passer une mémoire familiale (`family`) à `documented`.

## 4. Saisir (gabarits)

**Source** — ajouter dans `sources[]` (avant `s_arbre_filae`). `type` est
purement descriptif (`census`, `civil-record`, `military-record`, `press`…).
Le rendu choisit *lightbox* si `file` est une image, *nouvel onglet* si URL/PDF.

```json
{ "id": "s_recensement_1921_noyelles", "type": "census",
  "title": "Recensement de Noyelles-sous-Lens, 1921 — ménage de …",
  "repository": "Archives départementales du Pas-de-Calais",
  "citation": "Liste nominative 1921, ménage 341", "eventDate": "1921",
  "language": "français", "note": "Contenu et personnes du ménage…",
  "transcription": "Texte lisible de l'acte, \\n\\n séparant les paragraphes…",
  "transcriptionNote": "Transcription de travail (orthographe modernisée) ; passages incertains [?] / [...].",
  "shortLabel": "Recensement 1921", "file": "sources/Recensement1921….jpg" }
```

**Transcription (obligatoire pour tout manuscrit).** Dès qu'une source est un
**scan manuscrit d'un ancêtre** (acte paroissial/état civil, recensement, fiche
matricule…), ajouter le champ `transcription` avec le **texte lisible** de
l'acte — c'est le but même du déchiffrage. La lightbox l'affiche à côté du scan,
et le panneau des sources marque le document d'un « ✎ transcription » (rendu
automatique dès que le champ existe ; aucune autre action). Conventions :
- transcription de travail, **orthographe modernisée**, abréviations développées ;
- **passages illisibles** notés `[...]`, **lectures incertaines** `[?]` ;
- pour un **acte narratif** (baptême, mariage, décès), transcrire au fil du texte,
  paragraphes séparés par `\n\n` ; pour un **registre tabulaire** (recensement,
  succession), lister les champs ligne par ligne (`• Nom · prénom · année · …`) ;
- mettre les nuances éditoriales dans `transcriptionNote` (âge illisible, ligne
  masquée, coïncidence à confirmer…). Ne **jamais inventer** un passage non lu.
- **Double version (optionnelle)** : `transcriptionOriginal` = texte aux
  graphies d'époque telles que lues ; `transcription` reste la version
  **modernisée** (celle affichée par défaut). Quand les deux existent, la
  lightbox montre deux onglets « Modernisé / Texte d'époque ». Réserver le
  doublon aux pièces d'Ancien Régime où la graphie diffère vraiment ; noms
  propres et listes de noms identiques dans les deux versions.

**Événement** ajouté à une personne — `confidence` pilote le style de carte
(`documented`/`probable`/`family`/`unknown`). Types utiles : `birth`, `death`,
`occupation`, `residence`, `military`, `marriage` (sur l'union).

**Collatéral (frère/sœur)** — un enfant de l'union parentale **sans union
propre**. L'ajouter aux `children` de l'union des parents ; il se rend
automatiquement en carte « frère/sœur » à côté de son germain (voir CLAUDE.md,
`sibling_card`/`collateral_sibs_for`). Attention : les collatéraux d'un·e
conjoint·e **de tier `extended`** restent masqués ; ceux d'un·e conjoint·e
d'une union **visible** apparaissent dans l'arbre principal.

**Familles alliées** (ascendance des épouses) : `"tier": "extended"` sur la
personne **et** son union ; filiations `probable` (Filae) sauf preuve.

**Questions de recherche** : consigner les zones d'ombre (ligne masquée d'un
ménage, devenir d'une fratrie…) dans `researchQuestions[]`.

## 5. Rebuild + QA

```bash
python3 -c "import json; json.load(open('genealogie.json'))" && python3 build.py
```

Contrôle visuel headless (⚠ Chrome capture **depuis le haut et ignore le
scroll** ; fenêtre haute + recadrage) :

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --screenshot=/tmp/full.png --window-size=1500,7200 \
  --virtual-time-budget=6000 file://$PWD/index.html
tools/venv/bin/python tools/crop.py /tmp/full.png --box 0 4180 1500 5080   # zoomer la zone touchée
```

Vérifier : **hauteur uniforme** des cartes-couples préservée (ne pas déborder
`min-height` — trimmer le texte, ne pas gonfler `display.meta`), collatéraux au
bon endroit, liens de filiation cohérents. Nettoyer les PNG temporaires ensuite.

## Pièges déjà rencontrés

- Gonfler `display.meta` d'une carte-couple casse la grille uniforme → mettre le
  détail dans `events`/`notes` (visibles dans le modal), pas sur la carte.
- Ré-ajouter un scan quasi-identique déjà cité.
- Oublier de remonter la `confidence` d'un fait que le nouveau scan documente.
- Document trop récent / privé (CNI contemporaine) : ne pas citer ni utiliser en
  portrait.
