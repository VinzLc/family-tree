# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page, vintage-parchment-styled **French** genealogy site for the **Jastrzębski** (Galicia → Drohobycz → Noyelles-sous-Lens) and **Leclercq** (Harnes, ~1640 →) families. Reference person: Vincent Leclercq (b. 1995). Scope is the paternal lines only — the Molnar/Delporte maternal side was deliberately removed; Sylvie remains only as Jean-Marc's spouse leaf.

## Build & QA

```bash
python3 build.py          # regenerates index.html from genealogie.json
```

`build.py` uses only the Python stdlib — no dependencies, no test suite, no linter. There is no dev server; open `index.html` directly or render it headless for QA:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --screenshot=render.png --window-size=1320,3300 \
  file://$PWD/index.html
```

Chrome `--screenshot` captures the viewport **from the top and ignores scroll** — content below the window height is clipped. Use a tall `--window-size`, or note that `position:fixed` overlays (lightbox, modals, fullscreen map) always render at 0,0.

## Architecture: data-driven, single source of truth

`genealogie.json` → `python3 build.py` → `index.html`. **Never hand-edit `index.html`** — it is fully generated and gets overwritten. To change the site, edit the JSON (or `build.py` for markup/CSS/JS) and rebuild.

`build.py` is one file. The `Tree` class holds `people`/`unions`/`sources` dicts keyed by id, plus `partner_ids` (every id that is a union partner = an ancestor with a couple-card; union children NOT in this set are collaterals). It **BFS-walks ancestors** from `meta.rendering.rootUnionId` (currently `u_jeanmarc_sylvie`), one generation per level, rendering couple-cards. `render()` assembles: masthead → legend → branch-legend → tree → global allies toggle → gallery → map → sources panel → footer → person modal → lightbox.

**Tree layout & connectors.** All generations live in ONE horizontal-scroll canvas (`#treeScroll` → `#tree`) inside `#treeWrap`, each generation a centered `.gen-row[data-gen]`; each couple is wrapped in a `.union-core[data-uid]` and each person card carries `data-pid`. Generation labels live in a `#genLabels` overlay **outside** the scroll (fixed left gutter, never clipped); `TREE_JS`'s `placeLabels()` positions each `.gen-side[data-gen]` at the vertical centre of its matching `.gen-row`. The per-generation allies button (`.gen-ext-btn`) also lives in that overlay and toggles `.show-ext` on its row via `data-gen`. Filiation lines are drawn by JS (`TREE_JS`) into an absolutely-positioned `<svg id="treeLinks">` behind the cards: `tree_html()` emits `FATREE.links = [[childPersonId, parentUnionId, branchClass]]` and the script draws an elbow from **each child's own card top-centre** up to the parent-couple's bottom-centre — anchoring on the person (not the couple centre) is what makes "who descends from whom" legible. Recomputed on resize / allies-toggle / fonts-ready. `branches()` tags every ancestral union with the lineage it belongs to (`s0`/`s1` = the two grandparent branches, e.g. Jastrzębski vs Leclercq); links are coloured by the **parent's** branch (`.branch-s0` gall, `.branch-s1` oxblood, trunk = hair), and `.branch-legend` is the colour key. Because rows are merely centred (not positionally aligned to descendants), a deep single-line spine can lean once where the tree widens — this is expected; the coloured lines carry the descent.

### genealogie.json schema

- `meta.rendering` — masthead (`eyebrow`, `headline`, `route`, `continues`, `footer`), **`rootUnionId`** (tree entry point), `map`, `migration` (ordered `[fromKey, toKey]` place pairs for the polyline).
- `people[]` — `id` (prefix `p_`), `names{given,surname,marriedSurname,variants}`, `sex`, `parents.unionId`, `events[]` (`type`,`date`,`place`,`value`,`note`,`sources[]`,`confidence`), optional `notes`, optional `display{confidence,role,meta,src}`, optional `portrait{file,alt,source}`.
- `unions[]` — `id` (prefix `u_`), `partners` (1–2 person ids), `children[]`, `events[]` (marriage), optional `display{focal,marriageTag}`.
- `sources[]` — `id`, `title`, `shortLabel`, `file` (path in `sources/`, or an `http` URL), plus `repository`/`citation`/`coverage`.
- `researchQuestions[]`, `places{}`, `gallery{}`.

When a person has no explicit `display.*`, the card falls back to auto-generated `meta`/`role`/`src` derived from `events` (`auto_meta`, `auto_role`, `auto_src`).

## Domain conventions (respect these)

- **Confidence → card style** (`CONF_CLASS`): `documented`→`doc` (oxblood solid), `probable`/`inferred`→`prob` (gall dashed), `family`→`fam` (ochre solid, = family memory / told by user), `unknown`→`unk` (dotted). Do **not** mark a family-told fact as `documented`.
- **Uniform card height**: every couple-card shares ONE height — regular `.person:not(.sib)` = `min-height:216px`, focal `.person.focal` = `238px` (wider + emphasised). Cards are flex columns: `person_card()` wraps portrait+name+meta+role in `.p-body` and the `.src` line is pinned to the bottom (`margin-top:auto`) so short cards read as "body + footer", not a hole. The min-heights sit just above the tallest real card, so **if you add content that pushes a card past its min-height it will grow and break the uniform grid** — trim the text or bump both min-heights together. Collateral `.person.sib` cards are exempt (kept small).
- **`sources/`** = raw original scans the user provides (acts, passports, IDs, photos) — **never displayed raw**. **`img/`** = derived assets referenced by the HTML (cropped portraits, resized gallery photos). Keep these separate.
- **Privacy**: a too-recent / private document (e.g. a contemporary ID card) must not be referenced in `sources[]` or used as a `portrait`.
- **Allied families** (wives' ascendancy from `sources/Arbre.pdf`/Filae) carry `"tier": "extended"` on both the person AND the union. Extended stacks are **hidden by default** (`.stack.ext{display:none}`) and revealed two ways: a discreet per-generation button (`.gen-ext-btn` → toggles `.show-ext` on that row) and a global button at the **bottom** of the tree (`#showAllBtn` → toggles `.show-all`). Extended people are excluded from the map. All allied filiations are `probable` (Filae, unverified).
- **Collateral siblings**: a union child NOT in `partner_ids` (i.e. never married into the tree) renders as a minimal clickable "frère/sœur" card via `sibling_card()`. It sits **beside its sibling, same generation** — `union_stack` builds a `.union-row` = `[sibs of partner0] [.union-core couple] [sibs of partner1]`, so each sib group (`collateral_sibs_for(pid)` → `sib_group_html`) is on the *outer* side of the specific partner it belongs to. Sibs also get a filiation link to the parents' union (the link loop in `tree_html` walks partners **and** their collateral sibs), so a bracket forks from the shared parents to both children. To add one, put them in the parents' union `children` without giving them their own union; the data model is unchanged, only the render position. (E.g. Pierre Joseph Leclercq 1891–1914, mort pour la France, sits left of his brother Jules; Stanislas Jastrzębski sits left of his sister Janina.)
- **Pinned cousins (`treeCousin`)** — the ONE sanctioned exception to the ascendant-only tree. A person carrying `treeCousin: {besideUnion, label, linkTo}` (person-level, no `parents.unionId` needed) renders as a sib-style card (optional `display.tag` ribbon, e.g. "⚜ maire d'Harnes 1791-1798") in a labelled group on the LEFT of union `besideUnion` (one generation below their parent), and gets a filiation line drawn to the *person card* `linkTo` — TREE_JS `anchor()` accepts `p_` ids, and person-target links route up the free lane and enter the target card by its **side** (its bottom is hidden by the sib stack). Do NOT instead give the collateral parent a union: they'd enter `partner_ids`, drop out of the sibling row, and their union would never be BFS-walked — both would vanish. (E.g. Louis Valentin Leclercq 1726, son of collateral Jean Philippe, pinned beside Pierre Martin 1743's couple.)
- **z-index layering** — anything new must sit above Leaflet (~1000): fullscreen map 2000, person modal 2500, image lightbox 3000. This was a real bug (map bled over documents shown large).
- **Generation labels** auto-extend past *arrière-grands-parents* via `AIEUL_TERMS` (Trisaïeuls … Duodécaïeuls) + generation number.
- Source `file` paths are **URL-encoded** (`quote`) at build so scans with spaces/accents resolve. Image sources open in the shared lightbox (⌕ + download); URLs and PDFs open in a new tab (↗).

## Image tooling (this Mac has no ImageMagick, no system Pillow, no Quartz)

For crops/resizes/rotations, use a venv with Pillow. System `python3` is `/usr/bin/python3`. Google Chrome IS installed → use `--headless=new --screenshot` on the `file://` path for render QA, then Read the PNG.

## Interactivity (all client-side, emitted by build.py)

- **Person modal**: `person_detail()` builds a per-person dict → embedded `FAPEOPLE` JSON → `person_modal_html()` renders it. Cards hover-enlarge (CSS) and open the modal on click/Enter. Image source chips call `window.faShowImage` (exposed by the lightbox IIFE).
- **Map**: Leaflet + OSM-France tiles (sepia-filtered). `map_data()` aggregates events per place by matching `event.place` substrings against each place's `aliases`; migration segments get haversine distances. `⛶` toggles a fullscreen popup.

Online deps at render time: Google Fonts + Leaflet/OSM tiles. Everything else works offline.
