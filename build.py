#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — génère index.html à partir de genealogie.json.

Usage :  python3 build.py
La donnée vit dans genealogie.json ; ce script ne fait que la mettre en page.
Pour étoffer l'arbre : éditer le JSON puis relancer ce script.
"""
import json, math, os, re, sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "genealogie.json")
OUT_PATH = os.path.join(HERE, "index.html")

# ---------------------------------------------------------------- <head> + CSS
HEAD = r'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arbre généalogique — Jastrzębski · Leclercq</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js" crossorigin=""></script>
<style>
  :root{
    --parchment:#ece2cd;
    --parchment-card:#f4ecda;
    --ink:#2c2720;
    --ink-soft:#5a5142;
    --gall:#33536b;
    --oxblood:#8a3526;
    --ochre:#a9812f;
    --hair:#c6b896;
    --tree-edge:clamp(20px,3vw,72px);  /* marge du tree en plein-cadre (gouttière + bord) */
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  /* le tree en plein-cadre (width:100vw) ne doit jamais créer de scroll horizontal de page
     (100vw inclut la barre de défilement sur certains OS) — le scroll du tree est interne.
     overflow-x:hidden sur la racine ET le body bloque de façon fiable tout défilement
     horizontal global (clip seul laissait passer ~8px sur Chrome) ; le scroll de l'arbre
     est un conteneur interne (.tree-scroll) et reste intact. */
  html,body{overflow-x:hidden;}
  body{
    background:
      radial-gradient(circle at 18% 10%, rgba(169,129,47,.06), transparent 40%),
      radial-gradient(circle at 85% 65%, rgba(138,53,38,.05), transparent 45%),
      var(--parchment);
    color:var(--ink);
    font-family:"EB Garamond", Georgia, serif;
    font-size:17px; line-height:1.5;
    padding:44px 22px 64px;
    -webkit-font-smoothing:antialiased;
  }
  .sheet{max-width:1280px;margin:0 auto;}

  /* Masthead */
  header.masthead{text-align:center;margin-bottom:12px;}
  .eyebrow{
    font-family:"Courier Prime", monospace;text-transform:uppercase;
    letter-spacing:.4em;font-size:11.5px;color:var(--ink-soft);
    margin:0 0 14px;padding-left:.4em;
  }
  h1{
    font-family:"Cormorant Garamond", serif;font-weight:600;
    font-size:clamp(34px,6.2vw,58px);line-height:.98;margin:0;letter-spacing:.005em;
  }
  h1 .em{font-style:italic;color:var(--oxblood);font-weight:500;}
  h1 .amp{color:var(--ink-soft);font-style:italic;font-weight:400;}
  .route{
    font-family:"Cormorant Garamond", serif;font-size:clamp(17px,2.4vw,23px);
    font-style:italic;color:var(--ink-soft);margin:12px 0 0;
  }
  .route b{color:var(--gall);font-style:normal;font-weight:600;}
  .rule{width:100%;height:0;border-top:1.5px solid var(--ink);margin:22px 0 6px;position:relative;}
  .rule::after{
    content:"\2766";position:absolute;left:50%;top:-13px;transform:translateX(-50%);
    background:var(--parchment);padding:0 14px;color:var(--oxblood);font-size:18px;
  }

  /* Legend */
  .legend{
    display:flex;flex-wrap:wrap;gap:10px 24px;justify-content:center;
    font-size:14px;color:var(--ink-soft);margin:16px 0 34px;
    font-family:"Courier Prime", monospace;letter-spacing:.02em;
  }
  .legend span{display:inline-flex;align-items:center;gap:9px;}
  .chip{width:24px;height:16px;border-radius:2px;flex:none;}
  .chip.doc{background:var(--parchment-card);border:2px solid var(--oxblood);}
  .chip.prob{background:var(--parchment-card);border:2px dashed var(--gall);}
  .chip.fam{background:var(--parchment-card);border:2px solid var(--ochre);}
  .chip.unk{background:transparent;border:2px dotted var(--hair);}

  /* Tree — a single shared canvas so parent→child connector lines line up across generations */
  /* la gouttière des étiquettes vit HORS du scroll (jamais rognée), les rangées défilent à sa droite */
  /* le tree déborde du gabarit texte (max 1280) pour occuper toute la largeur écran :
     full-bleed centré dans le viewport — se centre si ça tient, défile sinon.
     La gouttière d'étiquettes (absolue) et le scroll sont insérés de --tree-edge
     pour ne pas coller au bord de l'écran ni être rognés. */
  .tree-wrap{position:relative;width:100vw;max-width:100vw;margin-left:calc(50% - 50vw);box-sizing:border-box;}
  .gen-labels{position:absolute;left:var(--tree-edge);top:0;width:150px;height:100%;pointer-events:none;z-index:5;}
  .tree-scroll{margin-left:calc(var(--tree-edge) + 154px);margin-right:var(--tree-edge);overflow-x:auto;overflow-y:hidden;padding:4px 0 12px;}
  .tree-scroll.is-scrollable{-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 26px,#000 calc(100% - 26px),transparent 100%);mask-image:linear-gradient(90deg,transparent 0,#000 26px,#000 calc(100% - 26px),transparent 100%);}
  .tree{position:relative;display:flex;flex-direction:column;align-items:center;width:max-content;min-width:100%;margin:0 auto;}
  /* filiation lines drawn behind the cards (JS-computed, so misaligned rows still connect) */
  .tree-links{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:visible;}
  .tree-links path{fill:none;stroke:var(--hair);stroke-width:1.5;stroke-linejoin:round;}
  .tree-links path.branch-s0{stroke:var(--gall);stroke-opacity:.6;stroke-width:2;}
  .tree-links path.branch-s1{stroke:var(--oxblood);stroke-opacity:.55;stroke-width:2;}
  /* légende des deux lignées (couleur des traits de filiation) */
  .branch-legend{display:flex;flex-wrap:wrap;gap:8px 26px;justify-content:center;margin:-14px 0 30px;
    font-family:"Courier Prime",monospace;font-size:12px;letter-spacing:.04em;color:var(--ink-soft);}
  .branch-legend span{display:inline-flex;align-items:center;gap:9px;}
  .branch-legend span::before{content:"";width:26px;height:0;border-top:3px solid var(--hair);flex:none;border-radius:2px;}
  .branch-legend .s0::before{border-color:var(--gall);}
  .branch-legend .s1::before{border-color:var(--oxblood);}
  .branch-legend b{color:var(--ink);font-family:"Cormorant Garamond",serif;font-size:16px;font-weight:600;letter-spacing:0;}
  /* étiquette de génération : fixée à gauche (hors scroll), centrée verticalement sur sa
     rangée par JS — laisse tout l'espace central/vertical libre pour les traits */
  .gen-row{align-self:stretch;display:flex;flex-direction:column;align-items:center;position:relative;z-index:1;}
  .gen-row + .gen-row{padding-top:54px;}
  .ancestors{display:flex;gap:52px;justify-content:center;align-items:flex-start;flex-wrap:nowrap;}
  /* étiquettes alignées à DROITE (vers les cartes) et collées au bord gauche de leur rangée
     par JS (placeLabels) : elles suivent la silhouette de l'arbre au lieu de rester au bord
     de l'écran loin des cartes centrées */
  .gen-side{position:absolute;left:0;width:150px;transform:translateY(-50%);
    display:flex;flex-direction:column;align-items:flex-end;gap:6px;padding-right:14px;pointer-events:none;}
  .gen-label{font-family:"Courier Prime", monospace;font-size:10.5px;letter-spacing:.18em;
    text-transform:uppercase;color:var(--ochre);text-align:right;line-height:1.62;margin:0;}
  .core-anchor{display:flex;gap:52px;align-items:flex-start;}
  .stack{display:flex;flex-direction:column;align-items:center;position:relative;}
  .union-core{display:flex;flex-direction:column;align-items:center;}
  .couple{display:flex;align-items:stretch;}
  .union-glyph{align-self:center;font-size:17px;color:var(--oxblood);padding:0 9px;flex:none;}
  /* familles alliées : masquées par défaut ; révélées globalement (.show-all) ou par génération (.show-ext) */
  .stack.ext{display:none;}
  .tree.show-all .stack.ext,
  .gen-row.show-ext .stack.ext{display:flex;}
  .gen-ext-btn{display:block;margin:0;font-family:"Courier Prime",monospace;font-size:9px;
    letter-spacing:.1em;text-transform:uppercase;color:var(--hair);background:none;border:none;
    padding:0;text-align:right;cursor:pointer;transition:color .15s;pointer-events:auto;}
  .gen-ext-btn:hover{color:var(--ochre);}
  .gen-ext-btn[aria-expanded="true"]{color:var(--ochre);}
  /* frères/sœurs (collatéraux) : petite carte À CÔTÉ de leur frère/sœur, même génération */
  .union-row{display:flex;align-items:center;gap:14px;}
  .sib-group{display:flex;flex-direction:column;align-items:center;gap:7px;align-self:center;}
  .sib-lbl{text-align:center;font-family:"Courier Prime",monospace;font-size:8px;letter-spacing:.16em;
    text-transform:uppercase;color:var(--ochre);margin-bottom:1px;}
  .person.sib{width:150px;padding:7px 10px 8px;}
  .person.sib .nm{font-size:15px;}
  .person.sib .meta{font-size:11.5px;}
  .sib-tag{display:block;color:var(--oxblood);font-style:italic;margin-top:1px;}
  .tree-toggle{text-align:center;margin:26px 0 4px;}
  .toggle-btn{font-family:"Courier Prime",monospace;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
    color:var(--gall);background:var(--parchment-card);border:1px solid var(--hair);border-radius:4px;
    padding:10px 20px;cursor:pointer;transition:border-color .15s,color .15s,background .15s;box-shadow:2px 3px 0 rgba(44,39,32,.05);}
  .toggle-btn:hover{border-color:var(--gall);color:var(--oxblood);background:#f7f0df;}
  .toggle-btn .tg-ic{color:var(--ochre);font-size:13px;}

  /* Person card — hauteur unique (le corps en haut, la source épinglée en bas) */
  .person{
    background:var(--parchment-card);border:2px solid var(--oxblood);border-radius:3px;
    padding:10px 13px 11px;width:180px;cursor:pointer;
    box-shadow:0 1px 0 rgba(44,39,32,.16), 2px 3px 0 rgba(44,39,32,.05);position:relative;
    transition:transform .15s ease, box-shadow .15s ease;
    display:flex;flex-direction:column;
  }
  .person:not(.sib){min-height:216px;}
  .p-body{width:100%;}
  .person.prob{border-style:dashed;border-color:var(--gall);}
  .person.unk{border-style:dotted;border-color:var(--hair);background:rgba(244,236,218,.5);}
  .person.fam{border-color:var(--ochre);}
  .person:hover{transform:translateY(-4px) scale(1.045);box-shadow:0 9px 24px rgba(44,39,32,.24);z-index:6;}
  .focal:hover{transform:translateY(-4px) scale(1.025);}
  .person::after{content:"⌕";position:absolute;bottom:5px;right:7px;font-size:12px;color:var(--ochre);opacity:0;transition:opacity .15s ease;pointer-events:none;}
  .person:hover::after{opacity:.7;}
  .person .nm{font-family:"Cormorant Garamond", serif;font-weight:600;font-size:19.5px;line-height:1.06;margin:0 0 3px;}
  .person.unk .nm{color:var(--ink-soft);font-style:italic;font-weight:500;}
  .person .meta{font-size:13.5px;color:var(--ink-soft);line-height:1.34;}
  .person .meta .yr{color:var(--gall);font-variant-numeric:tabular-nums;}
  .person .role{font-family:"Courier Prime", monospace;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ochre);margin-top:6px;display:block;}
  .person .src{font-family:"Courier Prime", monospace;font-size:9px;letter-spacing:.03em;color:var(--hair);margin-top:auto;padding-top:7px;display:block;}
  .cameo{float:right;width:52px;height:64px;object-fit:cover;border-radius:2px;border:1px solid #d6c6a2;
    margin:1px 0 5px 9px;filter:sepia(.32) contrast(1.03) brightness(1.02);box-shadow:1px 1px 0 rgba(44,39,32,.18);}
  .focal .cameo{width:60px;height:73px;}

  .person.focal{border:2.5px solid var(--oxblood);width:196px;min-height:238px;
    background:linear-gradient(180deg,#f7f0df,#f2e8d2);
    box-shadow:0 0 0 4px rgba(138,53,38,.08), 2px 4px 0 rgba(44,39,32,.08);}
  .focal .nm{font-size:22.5px;color:var(--oxblood);}
  .focal-band{display:flex;align-items:stretch;}
  .marriage-tag{text-align:center;font-style:italic;color:var(--ink-soft);font-size:14.5px;margin:9px 0 0;font-family:"Cormorant Garamond",serif;}
  .marriage-tag b{color:var(--gall);font-style:normal;font-weight:600;}
  .child .nm{font-style:italic;}
  .continues{font-family:"Cormorant Garamond",serif;font-style:italic;color:var(--ink-soft);font-size:17.5px;margin:14px 0 0;text-align:center;}
  .continues .dot{color:var(--ochre);}

  /* Panels */
  .panels{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:52px;}
  .panel{background:var(--parchment-card);border:1px solid var(--hair);border-top:3px solid var(--gall);border-radius:3px;padding:20px 22px 22px;}
  .panel.q{border-top-color:var(--oxblood);}
  .panel h2{font-family:"Courier Prime",monospace;font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:var(--gall);margin:0 0 15px;padding-left:.2em;}
  .panel.q h2{color:var(--oxblood);}
  .panel ul{margin:0;padding:0;list-style:none;}
  .panel li{padding:0 0 11px 21px;position:relative;font-size:15.5px;line-height:1.46;color:var(--ink);}
  .panel li:last-child{padding-bottom:0;}
  .panel li::before{content:"";position:absolute;left:2px;top:8px;width:7px;height:7px;background:var(--ochre);border-radius:50%;}
  .panel.q li::before{background:var(--oxblood);border-radius:1px;transform:rotate(45deg);}
  .panel li b{color:var(--gall);font-weight:600;}
  /* Panneau « histoire d'une graphie » (le Clercq -> Leclercq) */
  .nh-intro,.nh-p{font-size:15.5px;line-height:1.56;color:var(--ink);margin:0 0 12px;}
  .nh-p:last-child{margin-bottom:0;}
  .nh-flex{display:flex;gap:30px;align-items:flex-start;flex-wrap:wrap;margin:4px 0 16px;}
  .nh-table{border-collapse:collapse;flex:1 1 360px;min-width:300px;}
  .nh-table td{padding:7px 12px 7px 0;border-bottom:1px dotted var(--hair);vertical-align:baseline;}
  .nh-table tr:last-child td{border-bottom:none;}
  .nh-yr{font-family:"Courier Prime",monospace;font-size:12px;color:var(--ochre);white-space:nowrap;width:1%;}
  .nh-form{font-family:"Cormorant Garamond",serif;font-size:18px;font-style:italic;font-weight:600;}
  .nh-form.sep{color:var(--gall);}
  .nh-form.joined{color:var(--oxblood);}
  .nh-tag{font-family:"Courier Prime",monospace;font-size:9px;letter-spacing:.08em;text-transform:uppercase;border:1px solid currentColor;border-radius:9px;padding:1px 7px;margin-left:9px;white-space:nowrap;vertical-align:2px;}
  .nh-tag.sep{color:var(--gall);}
  .nh-tag.joined{color:var(--oxblood);}
  .nh-doc{font-size:13px;color:var(--ink-soft);}
  .nh-sig{flex:1 1 300px;min-width:260px;margin:6px 0 0;text-align:center;}
  .nh-sig img{max-width:100%;border:1px solid var(--hair);border-radius:2px;box-shadow:2px 3px 9px rgba(44,39,32,.2);cursor:zoom-in;}
  .nh-sig figcaption{font-size:12.5px;font-style:italic;color:var(--ink-soft);margin-top:8px;line-height:1.45;}
  .panel li .doc-name{font-style:italic;color:var(--ink-soft);}
  .panel li a.doc-name{text-decoration:none;cursor:pointer;}
  .panel li a.doc-name:hover{color:var(--oxblood);text-decoration:underline;}
  .panel li a.doc-name::after{content:" ↗";font-style:normal;color:var(--ochre);font-size:11px;}
  .panel li a.doc-name.doc-img{cursor:zoom-in;}
  .panel li a.doc-name.doc-img::after{content:" ⌕";font-style:normal;color:var(--ochre);font-size:14px;}
  /* Sources : catégories repliables */
  .src-intro{margin:-6px 0 8px;font-size:13px;font-style:italic;color:var(--ink-soft);}
  .src-cat{border-top:1px solid var(--hair);}
  .src-cat>summary{cursor:pointer;list-style:none;padding:11px 2px;display:flex;align-items:baseline;gap:9px;
    font-family:"Courier Prime",monospace;font-size:12px;letter-spacing:.13em;text-transform:uppercase;color:var(--ink-soft);}
  .src-cat>summary::-webkit-details-marker{display:none;}
  .src-cat>summary::before{content:"▸";color:var(--ochre);font-size:11px;line-height:1;transition:transform .15s ease;}
  .src-cat[open]>summary::before{transform:rotate(90deg);}
  .src-cat>summary:hover{color:var(--oxblood);}
  .src-cat>summary:hover::before{color:var(--oxblood);}
  .src-cat-name{flex:1;}
  .src-cat-meta{font-size:10px;letter-spacing:.04em;color:var(--gall);}
  .src-cat-count{font-size:12px;color:var(--ochre);font-variant-numeric:tabular-nums;}
  .src-cat[open]>summary{color:var(--gall);}
  .src-cat>ul{padding:2px 0 15px 3px;}

  /* Gallery */
  .gallery{margin-top:54px;}
  .gallery-title{font-family:"Courier Prime",monospace;font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:var(--ochre);text-align:center;margin:0 0 6px;}
  .gallery-sub{font-family:"Cormorant Garamond",serif;font-style:italic;text-align:center;color:var(--ink-soft);font-size:17px;margin:0 0 24px;}
  .gallery-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:22px;align-items:start;}
  .gallery figure{margin:0;background:var(--parchment-card);border:1px solid var(--hair);padding:9px 9px 11px;box-shadow:2px 3px 0 rgba(44,39,32,.05);}
  .gallery img{width:100%;height:auto;display:block;filter:sepia(.22) contrast(1.02);border:1px solid rgba(44,39,32,.08);}
  .gallery figcaption{font-family:"Cormorant Garamond",serif;font-style:italic;font-size:16px;color:var(--ink);margin-top:9px;text-align:center;line-height:1.32;}
  .gallery figcaption .cap-note{display:block;font-family:"Courier Prime",monospace;font-style:normal;font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--ochre);margin-top:4px;}

  /* Map */
  .famap-section{margin-top:54px;}
  .map-title{font-family:"Courier Prime",monospace;font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:var(--ochre);text-align:center;margin:0 0 6px;}
  .map-sub{font-family:"Cormorant Garamond",serif;font-style:italic;text-align:center;color:var(--ink-soft);font-size:17px;margin:0 0 24px;}
  #famap{height:540px;border:1px solid var(--hair);border-top:3px solid var(--gall);border-radius:3px;box-shadow:2px 3px 0 rgba(44,39,32,.05);background:#e7dcc4;}
  #famap .leaflet-tile-pane{filter:sepia(.45) saturate(.72) brightness(1.03) contrast(.96);}
  .leaflet-container{background:#e7dcc4;font-family:"EB Garamond",Georgia,serif;}
  .leaflet-bar a,.leaflet-bar a:hover{background:var(--parchment-card);color:var(--ink);border-bottom-color:var(--hair);}
  .leaflet-popup-content-wrapper{background:var(--parchment-card);color:var(--ink);border-radius:3px;border:1px solid var(--hair);box-shadow:2px 3px 0 rgba(44,39,32,.14);}
  .leaflet-popup-tip{background:var(--parchment-card);}
  .leaflet-popup-content{margin:11px 14px;font-size:13px;line-height:1.4;}
  .pl-card .pl-name{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:18px;color:var(--oxblood);display:block;margin-bottom:1px;}
  .pl-card .pl-detail{font-family:"Courier Prime",monospace;font-size:8.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ochre);display:block;margin-bottom:8px;}
  .pl-card ul{margin:0;padding-left:16px;}
  .pl-card li{margin-bottom:3px;color:var(--ink);}
  .pl-card .yr{color:var(--gall);font-variant-numeric:tabular-nums;}
  .pl-card li.pl-more{list-style:none;margin-left:-16px;font-style:italic;color:var(--ochre);}
  .leaflet-tooltip.place-tip{background:var(--parchment-card);border:1px solid var(--hair);border-radius:3px;color:var(--ink);box-shadow:2px 4px 10px rgba(44,39,32,.28);padding:10px 13px;width:270px;white-space:normal;text-align:left;font-family:"EB Garamond",Georgia,serif;font-size:13px;line-height:1.4;}
  .leaflet-tooltip.place-tip::before{display:none;}
  .leaflet-tooltip.dist-label{background:var(--parchment-card);border:1px solid var(--gall);color:var(--gall);font-family:"Courier Prime",monospace;font-size:10px;letter-spacing:.04em;padding:2px 8px;border-radius:11px;box-shadow:1px 1px 0 rgba(44,39,32,.12);white-space:nowrap;}
  .leaflet-tooltip.dist-label::before{display:none;}
  /* Route d'émigration : étapes numérotées, distances et trait ambré */
  .route-wp .rw-badge{display:flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#c17d1a;color:#fbf3e0;border:2px solid var(--parchment-card);box-shadow:1px 2px 4px rgba(44,39,32,.35);font-family:"Courier Prime",monospace;font-weight:700;font-size:12px;}
  .leaflet-tooltip.route-label{background:#7c4c12;border:none;color:#fbf3e0;font-family:"Courier Prime",monospace;font-size:10px;letter-spacing:.04em;padding:2px 8px;border-radius:11px;box-shadow:1px 1px 0 rgba(44,39,32,.2);white-space:nowrap;}
  .leaflet-tooltip.route-label::before{display:none;}
  .place-tip .rw-note{margin:7px 0 0;font-style:normal;color:var(--ink);}
  .fareg-chip.fareg-route{border-color:#c17d1a;color:#8a5410;background:#f6ead2;}
  .fareg-chip.fareg-route[aria-pressed="false"]{color:var(--ochre);background:var(--parchment-card);border-color:var(--hair);}
  /* Encart narratif : la route type des mineurs polonais */
  .route-panel{margin:20px 2px 0;padding:20px 22px;background:var(--parchment-card);border:1px solid var(--hair);border-left:4px solid #c17d1a;border-radius:3px;box-shadow:2px 3px 0 rgba(44,39,32,.05);}
  .route-title{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:22px;color:var(--oxblood);margin:0 0 6px;}
  .route-title .route-period{font-family:"Courier Prime",monospace;font-size:11px;letter-spacing:.08em;color:var(--ochre);text-transform:uppercase;vertical-align:middle;margin-left:6px;}
  .route-intro{font-family:"EB Garamond",Georgia,serif;font-size:15px;line-height:1.6;color:var(--ink);margin:0 0 16px;max-width:70ch;}
  .route-steps{list-style:none;margin:0;padding:0;}
  .route-steps li{display:flex;gap:13px;align-items:flex-start;padding:11px 0;border-top:1px dotted var(--hair);}
  .route-steps li:first-child{border-top:none;}
  .route-steps .rt-step{flex:none;display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:#c17d1a;color:#fbf3e0;font-family:"Courier Prime",monospace;font-weight:700;font-size:13px;margin-top:1px;}
  .route-steps .rt-name{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:18px;color:var(--ink);margin-right:9px;}
  .route-steps .rt-detail{font-family:"Courier Prime",monospace;font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--ochre);}
  .route-steps .rt-note{font-family:"EB Garamond",Georgia,serif;font-size:14px;line-height:1.55;color:var(--ink);margin:3px 0 0;max-width:68ch;}
  .route-total{margin:15px 0 0;font-family:"EB Garamond",Georgia,serif;font-size:13px;font-style:italic;color:var(--ochre);}
  .route-total b{font-style:normal;color:var(--oxblood);}
  /* Bulles de regroupement (cluster) annotées d'un nom de secteur */
  .fa-cluster{background:none;border:none;}
  .fa-cluster .fc-in{display:flex;align-items:center;gap:7px;background:var(--parchment-card);border:1px solid var(--oxblood);border-left:4px solid var(--oxblood);border-radius:15px;padding:3px 11px 3px 4px;box-shadow:2px 3px 0 rgba(44,39,32,.16);white-space:nowrap;cursor:pointer;transition:transform .1s;}
  .fa-cluster:hover .fc-in{transform:translateY(-1px);}
  .fa-cluster .fc-num{flex:none;display:flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 5px;border-radius:11px;background:var(--oxblood);color:var(--parchment);font-family:"Courier Prime",monospace;font-weight:700;font-size:12px;}
  .fa-cluster .fc-name{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:15px;color:var(--oxblood);line-height:1.05;}
  .fa-cluster .fc-hint{font-family:"Courier Prime",monospace;font-size:8px;letter-spacing:.08em;text-transform:uppercase;color:var(--ochre);display:block;}
  /* Barre de raccourcis vers chaque secteur */
  .faregions{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:0 2px 10px;}
  .faregions .fr-lead{font-family:"Courier Prime",monospace;font-size:9px;letter-spacing:.09em;text-transform:uppercase;color:var(--ochre);margin-right:1px;}
  .fareg-chip{font-family:"EB Garamond",Georgia,serif;font-size:13px;color:var(--oxblood);background:var(--parchment-card);border:1px solid var(--hair);border-radius:14px;padding:3px 12px;cursor:pointer;transition:background .12s,border-color .12s;}
  .fareg-chip:hover,.fareg-chip:focus{background:#f0e7d4;border-color:var(--oxblood);outline:none;}
  .fareg-chip[data-reg="_all"]{color:var(--ink);}
  /* Étiquette permanente pour un point resté isolé (hors cluster) */
  .leaflet-tooltip.pl-name-lbl{background:var(--parchment-card);border:1px solid var(--oxblood);color:var(--oxblood);font-family:"Cormorant Garamond",serif;font-weight:600;font-size:13.5px;line-height:1;padding:2px 8px;border-radius:12px;box-shadow:1px 2px 0 rgba(44,39,32,.14);white-space:nowrap;}
  .leaflet-tooltip.pl-name-lbl::before{display:none;}

  /* Fullscreen map */
  .map-fs-hint{font-family:"Courier Prime",monospace;font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--hair);text-align:right;margin:6px 2px 0;}
  .mapfull-backdrop{position:fixed;inset:0;background:rgba(20,16,10,.93);display:none;z-index:2000;}
  .mapfull-backdrop.open{display:block;}
  #mapfull-holder{position:absolute;inset:30px;border:6px solid var(--parchment-card);box-shadow:0 8px 50px rgba(0,0,0,.55);overflow:hidden;border-radius:2px;}
  .mapfull-backdrop #famap{height:100%!important;width:100%;border:none;border-radius:0;box-shadow:none;}
  .mapfull-close{position:fixed;top:13px;right:22px;color:var(--parchment);font-size:30px;line-height:1;cursor:pointer;background:none;border:none;font-family:"Courier Prime",monospace;z-index:2001;}

  /* Lightbox (au-dessus de la carte Leaflet, z-index ~1000) */
  .gallery img{cursor:zoom-in;}
  .lb-backdrop{position:fixed;inset:0;background:rgba(20,16,10,.88);display:none;align-items:center;justify-content:center;z-index:3000;padding:30px;cursor:zoom-out;}
  .lb-backdrop.open{display:flex;}
  .lb-stage{display:flex;gap:20px;align-items:stretch;max-width:96vw;max-height:88vh;cursor:default;}
  .lb-figure{margin:0;display:flex;flex-direction:column;align-items:center;min-width:0;}
  .lb-figure img{max-width:min(90vw,960px);max-height:82vh;width:auto;height:auto;border:6px solid var(--parchment-card);box-shadow:0 8px 50px rgba(0,0,0,.55);}
  .lb-stage.has-trans .lb-figure img{max-width:min(56vw,760px);}
  .lb-cap{color:var(--parchment);font-family:"Cormorant Garamond",serif;font-style:italic;font-size:18px;margin-top:14px;text-align:center;}
  .lb-close{position:fixed;top:16px;right:24px;color:var(--parchment);font-size:32px;line-height:1;cursor:pointer;font-family:"Courier Prime",monospace;z-index:3001;}
  .lb-dl{display:inline-block;margin-top:13px;color:var(--parchment);font-family:"Courier Prime",monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none;border:1px solid rgba(244,236,218,.55);border-radius:3px;padding:7px 17px;cursor:pointer;transition:background .15s,border-color .15s;}
  .lb-dl:hover{background:rgba(244,236,218,.13);border-color:var(--parchment);}
  /* Bande de vignettes (documents à plusieurs vues) */
  .lb-thumbs{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:12px;max-width:min(90vw,760px);}
  .lb-thumbs[hidden]{display:none;}
  .lb-thumbs img{width:60px;height:60px;object-fit:cover;border:2px solid rgba(244,236,218,.35);border-radius:2px;cursor:pointer;opacity:.7;transition:opacity .12s,border-color .12s;}
  .lb-thumbs img:hover{opacity:1;}
  .lb-thumbs img.active{border-color:var(--parchment);opacity:1;}
  /* Panneau de transcription du manuscrit */
  .lb-trans{width:min(40vw,470px);flex:none;background:var(--parchment-card);border:1px solid var(--hair);border-top:3px solid var(--gall);border-radius:3px;padding:17px 21px;overflow:auto;max-height:82vh;text-align:left;box-shadow:0 8px 50px rgba(0,0,0,.4);}
  .lb-trans[hidden]{display:none;}
  .lb-trans h3{font-family:"Courier Prime",monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ochre);margin:0 0 4px;}
  .lb-trans .lb-trans-doc{font-family:"Cormorant Garamond",serif;font-size:17px;color:var(--oxblood);margin:0 0 12px;border-bottom:1px solid var(--hair);padding-bottom:9px;}
  .lb-trans-body{white-space:pre-wrap;font-family:"EB Garamond",Georgia,serif;font-size:14px;line-height:1.62;color:var(--ink);}
  .lb-trans-tabs{display:flex;gap:7px;margin:0 0 12px;}
  .lb-trans-tabs button{font-family:"Courier Prime",monospace;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;padding:3px 11px;border:1px solid var(--hair);background:transparent;color:var(--ink-soft);border-radius:11px;cursor:pointer;}
  .lb-trans-tabs button.active{border-color:var(--gall);color:var(--gall);background:rgba(51,83,107,.08);}
  .lb-trans-note{margin:13px 0 0;padding-top:10px;border-top:1px dotted var(--hair);font-size:11px;font-style:italic;line-height:1.5;color:var(--ochre);}
  .doc-transflag{margin-left:7px;font-family:"Courier Prime",monospace;font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--gall);white-space:nowrap;}
  .doc-concerns{display:block;font-size:12.5px;font-style:italic;color:var(--ink-soft);margin-top:3px;line-height:1.45;}
  @media(max-width:860px){
    .lb-stage{flex-direction:column;max-height:90vh;overflow:auto;}
    .lb-stage.has-trans .lb-figure img,.lb-figure img{max-width:88vw;max-height:56vh;}
    .lb-trans{width:auto;max-height:none;}
  }

  /* Person detail modal (au-dessus de la carte, sous la lightbox) */
  .pcard-backdrop{position:fixed;inset:0;background:rgba(20,16,10,.82);display:none;align-items:center;justify-content:center;z-index:2500;padding:24px;}
  .pcard-backdrop.open{display:flex;}
  .pcard{background:var(--parchment-card);border:1px solid var(--hair);border-top:5px solid var(--oxblood);border-radius:4px;max-width:580px;width:100%;max-height:88vh;overflow:auto;padding:26px 30px 28px;box-shadow:0 14px 64px rgba(0,0,0,.5);position:relative;animation:pcin .18s ease;}
  .pcard.prob{border-top-color:var(--gall);} .pcard.fam{border-top-color:var(--ochre);} .pcard.unk{border-top-color:var(--hair);}
  @keyframes pcin{from{opacity:0;transform:translateY(14px) scale(.97);}to{opacity:1;transform:none;}}
  .pcard-close{position:absolute;top:9px;right:15px;background:none;border:none;font-family:"Courier Prime",monospace;font-size:27px;color:var(--ink-soft);cursor:pointer;line-height:1;}
  .pcard-close:hover{color:var(--oxblood);}
  .pcard-head{display:flex;gap:18px;align-items:flex-start;border-bottom:1px solid var(--hair);padding-bottom:17px;margin-bottom:17px;}
  .pcard-photo{display:block;max-width:190px;width:58%;height:auto;border:1px solid #d6c6a2;border-radius:2px;filter:sepia(.3) contrast(1.03);box-shadow:1px 1px 0 rgba(44,39,32,.18);cursor:zoom-in;}
  .pcard-photo-cap{display:block;font-style:italic;font-size:13px;line-height:1.4;color:var(--ink-soft);margin-top:7px;max-width:280px;}
  .pcard-conf{font-family:"Courier Prime",monospace;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--oxblood);}
  .pcard-name{font-family:"Cormorant Garamond",serif;font-weight:600;font-size:29px;line-height:1.04;margin:3px 0 5px;color:var(--ink);}
  .pcard-name small{display:block;font-size:15px;font-style:italic;font-weight:400;color:var(--ink-soft);}
  .pcard-role{font-family:"Courier Prime",monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ochre);margin:0;}
  .pcard-sec{margin-bottom:18px;} .pcard-sec:last-child{margin-bottom:0;}
  .pcard-sec h4{font-family:"Courier Prime",monospace;font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--gall);margin:0 0 10px;}
  .pd-ev{display:flex;gap:14px;margin-bottom:9px;font-size:15px;line-height:1.4;}
  .pd-l{flex:0 0 116px;color:var(--ochre);font-family:"Courier Prime",monospace;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;padding-top:4px;}
  .pd-v{color:var(--ink);} .pd-v .yr{color:var(--gall);font-variant-numeric:tabular-nums;}
  .pd-n{display:block;color:var(--ink-soft);font-style:italic;font-size:13.5px;margin-top:2px;}
  .pcard-fam{font-size:15px;line-height:1.55;color:var(--ink);}
  .pcard-fam b{color:var(--gall);font-weight:600;} .pcard-fam .kids{color:var(--ink-soft);font-style:italic;}
  .pd-desc-sp{font-size:15px;color:var(--ink);margin:0 0 8px;} .pd-desc-sp b{color:var(--gall);font-weight:600;}
  .pd-desc-row{display:flex;justify-content:space-between;gap:14px;font-size:14.5px;line-height:1.5;padding:3px 0;border-bottom:1px dotted rgba(44,39,32,.13);}
  .pd-desc-row:last-of-type{border-bottom:none;}
  .pd-desc-d{flex:none;color:var(--gall);font-variant-numeric:tabular-nums;font-size:13px;}
  .pd-desc-note{font-style:italic;color:var(--ink-soft);font-size:13px;margin:8px 0 0;}
  .pcard-notes{font-style:italic;color:var(--ink-soft);font-size:14.5px;line-height:1.55;}
  .pcard-src{display:flex;flex-wrap:wrap;gap:8px;}
  .pcard-src a{font-family:"Courier Prime",monospace;font-size:11px;letter-spacing:.02em;color:var(--ink-soft);text-decoration:none;border:1px solid var(--hair);border-radius:3px;padding:5px 10px;cursor:pointer;background:rgba(255,255,255,.25);}
  .pcard-src a:hover{color:var(--oxblood);border-color:var(--oxblood);}
  .pcard-src a .mk{color:var(--ochre);}

  footer{margin-top:44px;text-align:center;font-family:"Courier Prime",monospace;font-size:11px;letter-spacing:.1em;color:var(--ink-soft);line-height:1.7;}
  footer .seal{color:var(--oxblood);font-size:15px;display:block;margin-bottom:8px;letter-spacing:0;}

  @media (max-width:780px){
    body{font-size:15px;padding:28px 12px 48px;}
    :root{--tree-edge:8px;}
    .person,.focal{width:min(86vw,260px);}
    .panels{grid-template-columns:1fr;gap:16px;}
    .gen-labels,.gen-side{width:104px;}
    .gen-label{font-size:9px;letter-spacing:.12em;}
    .tree-scroll{margin-left:calc(var(--tree-edge) + 108px);}
  }
  @media print{
    body{background:#fff;padding:0;}
    .person,.focal,.panel{box-shadow:none;}
    *{print-color-adjust:exact;-webkit-print-color-adjust:exact;}
  }
</style>
</head>
'''

MONTHS = [None, "janvier", "février", "mars", "avril", "mai", "juin",
          "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
CONF_CLASS = {"documented": "doc", "probable": "prob", "inferred": "prob",
              "unknown": "unk", "family": "fam"}
PRIORITY = {"high": 0, "medium": 1, "low": 2}
# Termes d'ascendance au-delà des arrière-grands-parents (génération n)
AIEUL_TERMS = {4: "Trisaïeuls", 5: "Quadrisaïeuls", 6: "Quintaïeuls", 7: "Sextaïeuls",
               8: "Septaïeuls", 9: "Octaïeuls", 10: "Nonaïeuls", 11: "Décaïeuls",
               12: "Undécaïeuls", 13: "Duodécaïeuls"}
EVENT_LABELS = {"birth": "Naissance", "baptism": "Baptême", "death": "Décès",
                "occupation": "Profession", "military": "Service militaire",
                "residence": "Résidence", "marriage": "Mariage", "religion": "Religion",
                "civic": "Vie communale"}
CONF_LABEL = {"documented": "Documenté · acte", "probable": "Probable · index/arbre",
              "inferred": "Déduit", "family": "Mémoire familiale", "unknown": "À retrouver"}

MAP_INIT_JS = '''<script>
(function(){
  if (typeof L === "undefined" || !document.getElementById("famap")) return;
  var idx = {}; FAMAP.places.forEach(function(p){ idx[p.key] = p; });
  var famapEl = document.getElementById("famap"), home = famapEl.parentNode;
  var map = L.map("famap", {scrollWheelZoom:false, zoomControl:false});
  map.attributionControl.setPrefix("");
  L.control.zoom({zoomInTitle:"Zoomer", zoomOutTitle:"Dézoomer"}).addTo(map);
  L.tileLayer("https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
    {maxZoom:19, attribution:"© OpenStreetMap France · © les contributeurs OpenStreetMap"}).addTo(map);
  (FAMAP.migration||[]).forEach(function(seg){
    var a=idx[seg.from], b=idx[seg.to];
    if(!a||!b) return;
    L.polyline([[a.lat,a.lon],[b.lat,b.lon]],
      {color:"#33536b",weight:2,dashArray:"5,7",opacity:.85}).addTo(map)
      .bindTooltip(seg.label,{permanent:true,direction:"center",className:"dist-label"});
  });
  // Nom d'un secteur (region) → utilisé pour annoter les bulles de regroupement
  var regMeta={}; (FAMAP.regions||[]).forEach(function(r){ regMeta[r.key]=r; });
  // Bulle de cluster annotée du nom de secteur + nombre de lieux regroupés
  function clusterIcon(cluster){
    var kids=cluster.getAllChildMarkers(), reg=kids.length?kids[0].faRegion:"";
    var meta=regMeta[reg]||{name:"Lieux",detail:""}, n=cluster.getChildCount();
    var html='<div class="fc-in"><span class="fc-num">'+n+'</span><span>'+
      '<span class="fc-name">'+meta.name+'</span>'+
      (meta.detail?'<span class="fc-hint">'+meta.detail+'</span>':'')+'</span></div>';
    return L.divIcon({html:html,className:"fa-cluster",iconSize:null});
  }
  var useCluster=(typeof L.markerClusterGroup==="function");
  var group=useCluster?L.markerClusterGroup({
      showCoverageOnHover:false, spiderfyOnMaxZoom:true, zoomToBoundsOnClick:true,
      maxClusterRadius:48, disableClusteringAtZoom:11, iconCreateFunction:clusterIcon
    }):L.layerGroup();
  var pts=[], regPts={}, markers=[], labels=[];
  FAMAP.places.forEach(function(p){
    var head='<div class="pl-card"><span class="pl-name">'+p.name+'</span>'+
          '<span class="pl-detail">'+p.detail+'</span>';
    var full=head+'<ul>';
    p.events.forEach(function(e){ full+='<li>'+e+'</li>'; });
    full+='</ul></div>';
    var N=8, tip=head+'<ul>';
    p.events.slice(0,N).forEach(function(e){ tip+='<li>'+e+'</li>'; });
    if(p.events.length>N) tip+='<li class="pl-more">… et '+(p.events.length-N)+' autres événements</li>';
    tip+='</ul></div>';
    var r=Math.min(6+Math.round(p.events.length/3),12);
    var mk=L.circleMarker([p.lat,p.lon],
      {radius:r,color:"#f4ecda",weight:2,fillColor:"#8a3526",fillOpacity:1});
    mk.faRegion=p.region||"";
    mk.bindTooltip(tip,{direction:"auto",className:"place-tip",opacity:1});
    mk.bindPopup(full);
    group.addLayer(mk);
    // étiquette permanente affichée seulement quand le point reste isolé (hors bulle)
    var lbl=L.tooltip({permanent:true,direction:"top",offset:[0,-r-1],
      className:"pl-name-lbl",opacity:1}).setLatLng([p.lat,p.lon]).setContent(p.name);
    markers.push(mk); labels.push(lbl);
    pts.push([p.lat,p.lon]);
    if(p.region){ (regPts[p.region]=regPts[p.region]||[]).push([p.lat,p.lon]); }
  });
  map.addLayer(group);
  // --- route d'émigration (reconstitution historique) : trait ambré + étapes numérotées ---
  var routeLayer=null, routePts=[];
  if(FAMAP.route && FAMAP.route.waypoints){
    routeLayer=L.layerGroup();
    var wps=FAMAP.route.waypoints, latlngs=wps.map(function(w){return [w.lat,w.lon];});
    routePts=latlngs.slice();
    L.polyline(latlngs,{color:"#f4ecda",weight:6,opacity:.55}).addTo(routeLayer);
    L.polyline(latlngs,{color:"#c17d1a",weight:3,opacity:.95,dashArray:"1,9",lineCap:"round"}).addTo(routeLayer);
    (FAMAP.route.segments||[]).forEach(function(s){
      L.polyline([s.from,s.to],{opacity:0,weight:10}).addTo(routeLayer)
        .bindTooltip(s.label,{permanent:true,direction:"center",className:"route-label"});
    });
    wps.forEach(function(w){
      var badge=L.marker([w.lat,w.lon],{icon:L.divIcon({className:"route-wp",
        html:'<span class="rw-badge">'+w.step+'</span>',iconSize:[24,24],iconAnchor:[12,12]}),
        zIndexOffset:1500}).addTo(routeLayer);
      var tip='<div class="pl-card"><span class="pl-name">'+w.name+'</span>'+
        '<span class="pl-detail">'+(w.detail||"")+'</span><p class="rw-note">'+(w.note||"")+'</p></div>';
      badge.bindTooltip(tip,{direction:"top",className:"place-tip",opacity:1});
    });
    map.addLayer(routeLayer);
  }
  var routeBtn=document.getElementById("faRouteBtn");
  if(routeBtn && routeLayer){
    routeBtn.addEventListener("click",function(){
      if(map.hasLayer(routeLayer)){ map.removeLayer(routeLayer);
        routeBtn.textContent="＋ Route d’émigration 1929"; routeBtn.setAttribute("aria-pressed","false"); }
      else { map.addLayer(routeLayer);
        routeBtn.textContent="✕ Route d’émigration 1929"; routeBtn.setAttribute("aria-pressed","true"); }
    });
  }
  // Un point est « isolé » si markercluster ne l'a pas absorbé dans une bulle.
  // (getVisibleParent est inutilisable ici : il remonte via ._icon, absent des
  //  circleMarker ; on teste donc directement la présence du marqueur sur la carte.)
  function syncLabels(){
    markers.forEach(function(mk,i){
      var alone=!useCluster || map.hasLayer(mk);
      var lbl=labels[i];
      if(alone && !map.hasLayer(lbl)) lbl.addTo(map);
      else if(!alone && map.hasLayer(lbl)) map.removeLayer(lbl);
    });
  }
  if(useCluster){ group.on("animationend",syncLabels); }
  map.on("moveend zoomend",syncLabels);
  function fit(){ var all=pts.concat(routePts); if(all.length) map.fitBounds(all,{padding:[62,62]}); }
  fit();
  setTimeout(syncLabels,120); setTimeout(syncLabels,500);

  // --- raccourcis « Secteurs » : zoom sur un cluster nommé ---
  var chipBar=document.getElementById("faRegions");
  if(chipBar){
    chipBar.addEventListener("click",function(e){
      var b=e.target.closest(".fareg-chip"); if(!b) return;
      var k=b.getAttribute("data-reg");
      if(k==="_all"){ fit(); return; }
      var rp=regPts[k];
      if(rp&&rp.length) map.fitBounds(rp,{padding:[70,70],maxZoom:13});
    });
  }

  // --- plein écran ---
  var modal=document.getElementById("mapfull"), holder=document.getElementById("mapfull-holder");
  function refresh(){ setTimeout(function(){ map.invalidateSize(); fit(); syncLabels(); }, 80); }
  function openFull(){ if(modal){ holder.appendChild(famapEl); modal.classList.add("open"); refresh(); } }
  function closeFull(){ if(modal){ home.appendChild(famapEl); modal.classList.remove("open"); refresh(); } }
  var Full=L.Control.extend({options:{position:"topleft"}, onAdd:function(){
    var d=L.DomUtil.create("div","leaflet-bar leaflet-control");
    var a=L.DomUtil.create("a","",d);
    a.href="#"; a.title="Plein écran"; a.innerHTML="⛶"; a.style.fontWeight="700";
    L.DomEvent.on(a,"click",function(e){ L.DomEvent.stop(e); openFull(); });
    return d;
  }});
  map.addControl(new Full());
  if(modal){
    document.getElementById("mapfullClose").addEventListener("click",closeFull);
    modal.addEventListener("click",function(e){ if(e.target===modal) closeFull(); });
    document.addEventListener("keydown",function(e){ if(e.key==="Escape" && modal.classList.contains("open")) closeFull(); });
  }
})();
</script>'''


TREE_JS = r'''<script>
(function(){
  var scroll=document.getElementById("treeScroll"),
      tree=document.getElementById("tree"),
      svg=document.getElementById("treeLinks");
  if(!tree||!svg) return;
  var links=(window.FATREE&&FATREE.links)||[];
  var pN=svg.querySelector("path:not([class])"),
      p0=svg.querySelector(".branch-s0"), p1=svg.querySelector(".branch-s1");
  function anchor(uid){
    // cible normale : un couple (union-core) ; exception treeCousin : la carte
    // d'une personne (parent collatéral), identifiée par son préfixe p_
    return uid.indexOf("p_")===0
      ? tree.querySelector('.person[data-pid="'+uid+'"]')
      : tree.querySelector('.union-core[data-uid="'+uid+'"]');
  }
  function draw(){
    var base=tree.getBoundingClientRect(), W=tree.scrollWidth, H=tree.scrollHeight;
    svg.setAttribute("width",W); svg.setAttribute("height",H);
    svg.setAttribute("viewBox","0 0 "+W+" "+H);
    var dN="", d0="", d1="";
    function add(cls,seg){ if(cls==="s0") d0+=seg; else if(cls==="s1") d1+=seg; else dN+=seg; }
    // Regroupe les liens par union parente : un SEUL palier par fratrie, et les
    // collatéraux empilés (.sib) partagent une épine latérale (un taquet par carte)
    // au lieu d'un coude chacun — sinon les paliers superposés font un quadrillage.
    var groups={}, order=[];
    links.forEach(function(l){
      var childEl=tree.querySelector('.person[data-pid="'+l[0]+'"]'), parEl=anchor(l[1]);
      if(!childEl||!parEl) return;
      var cr=childEl.getBoundingClientRect(), pr=parEl.getBoundingClientRect();
      if(!cr.width||!pr.width) return;                  // masqué (allié replié)
      if(!groups[l[1]]){ groups[l[1]]={pr:pr,cls:l[2],items:[],person:l[1].indexOf("p_")===0}; order.push(l[1]); }
      groups[l[1]].items.push({el:childEl,r:cr});
    });
    order.forEach(function(uid){
      var g=groups[uid];
      var px=Math.round(g.pr.left-base.left+g.pr.width/2), pyBot=Math.round(g.pr.bottom-base.top);
      var minTop=Infinity;
      g.items.forEach(function(it){ minTop=Math.min(minTop,it.r.top-base.top); });
      var midY=Math.round((minTop+pyBot)/2);
      var stacks=[];                                    // une épine par .sib-group
      g.items.forEach(function(it){
        if(!it.el.classList.contains("sib")){
          // enfant direct : remonte de sa carte → palier commun → couple parent
          var cx=Math.round(it.r.left-base.left+it.r.width/2), cyTop=Math.round(it.r.top-base.top);
          add(g.cls,"M"+cx+" "+cyTop+"V"+midY+"H"+px+"V"+pyBot);
          return;
        }
        var box=it.el.closest(".sib-group"), st=null;
        for(var i=0;i<stacks.length;i++) if(stacks[i].box===box){ st=stacks[i]; break; }
        if(!st){ st={box:box,cards:[]}; stacks.push(st); }
        st.cards.push(it.r);
      });
      stacks.forEach(function(st){
        var left=!(st.box&&st.box.classList.contains("right")); // épine côté extérieur
        var spineX=null, lowY=-Infinity, seg="";
        st.cards.forEach(function(r){
          var x=Math.round((left?r.left:r.right)-base.left)+(left?-12:12);
          spineX=spineX===null?x:(left?Math.min(spineX,x):Math.max(spineX,x));
        });
        st.cards.forEach(function(r){
          var y=Math.round(r.top-base.top+r.height/2), ex=Math.round((left?r.left:r.right)-base.left);
          seg+="M"+ex+" "+y+"H"+spineX; lowY=Math.max(lowY,y);
        });
        if(g.person){
          // cible = carte d'une personne (treeCousin) : on reste dans le couloir
          // latéral et on entre par le CÔTÉ de la carte, jamais par en dessous
          // (le bas est masqué par la pile de frères/sœurs)
          var py=Math.round(g.pr.top-base.top+g.pr.height/2);
          var side=spineX<Math.round(g.pr.left-base.left)?g.pr.left:g.pr.right;
          seg+="M"+spineX+" "+lowY+"V"+py+"H"+Math.round(side-base.left);
        } else {
          seg+="M"+spineX+" "+lowY+"V"+midY+"H"+px+"V"+pyBot;
        }
        add(g.cls,seg);
      });
    });
    pN.setAttribute("d",dN); p0.setAttribute("d",d0); p1.setAttribute("d",d1);
  }
  function scrollable(){ scroll.classList.toggle("is-scrollable", tree.scrollWidth>scroll.clientWidth+1); }
  function center(){ scroll.scrollLeft=Math.max(0,(tree.scrollWidth-scroll.clientWidth)/2); }
  // place chaque étiquette (hors scroll) en face de sa rangée : centrée verticalement, et
  // — quand l'arbre tient sans défilement — collée juste à gauche de la carte la plus à
  // gauche de sa rangée (les rangées étroites sont centrées, l'étiquette les suit au lieu de
  // rester au bord de l'écran). Si l'arbre défile, l'étiquette reste dans la gouttière fixe.
  var wrap=document.getElementById("treeWrap"), labelBox=document.getElementById("genLabels");
  function placeLabels(){
    if(!wrap||!labelBox) return;
    var wy=wrap.getBoundingClientRect().top;
    var lbLeft=labelBox.getBoundingClientRect().left;   // origine horizontale des .gen-side
    var fits=tree.scrollWidth<=scroll.clientWidth+1;     // l'arbre tient sans défiler
    labelBox.querySelectorAll(".gen-side").forEach(function(side){
      var row=tree.querySelector('.gen-row[data-gen="'+side.dataset.gen+'"]');
      if(!row) return;
      var r=row.getBoundingClientRect();
      side.style.top=((r.top+r.bottom)/2 - wy)+"px";
      if(!fits){ side.style.left=""; return; }            // défilement : gouttière fixe (CSS)
      var minLeft=Infinity;
      row.querySelectorAll(".person").forEach(function(c){
        var cr=c.getBoundingClientRect(); if(cr.width) minLeft=Math.min(minLeft,cr.left);
      });
      if(minLeft===Infinity){ side.style.left=""; return; }
      // bord droit de l'étiquette aligné sur le bord gauche de la carte (padding = l'écart)
      side.style.left=Math.max(0, minLeft - side.offsetWidth - lbLeft)+"px";
    });
  }
  function refresh(){ draw(); scrollable(); placeLabels(); }
  function extBtns(){ return labelBox?labelBox.querySelectorAll(".gen-ext-btn"):[]; }
  extBtns().forEach(function(gb){
    var row=tree.querySelector('.gen-row[data-gen="'+gb.dataset.gen+'"]');
    gb.addEventListener("click",function(){
      var on=row.classList.toggle("show-ext");
      gb.setAttribute("aria-expanded",on?"true":"false");
      gb.textContent=on?"− masquer cette génération":("＋ "+gb.dataset.n+" allié"+(gb.dataset.n>1?"s":""));
      refresh(); center();
    });
  });
  var b=document.getElementById("showAllBtn");
  if(b){
    var sMore='<span class="tg-ic">⊕</span> Afficher toutes les familles alliées (Lesire, Léonard, Dufour…)';
    var sLess='<span class="tg-ic">⊖</span> Masquer toutes les familles alliées';
    b.addEventListener("click",function(){
      var on=tree.classList.toggle("show-all");
      b.innerHTML=on?sLess:sMore; b.setAttribute("aria-expanded",on?"true":"false");
      extBtns().forEach(function(gb){
        gb.setAttribute("aria-expanded",on?"true":"false");
        gb.textContent=on?"− masquer cette génération":("＋ "+gb.dataset.n+" allié"+(gb.dataset.n>1?"s":""));
      });
      refresh(); center();
    });
  }
  refresh(); center();
  window.addEventListener("resize",function(){ refresh(); center(); });
  window.addEventListener("load",function(){ refresh(); center(); });
  if(document.fonts&&document.fonts.ready){ document.fonts.ready.then(function(){ refresh(); center(); }); }
})();
</script>'''


def esc(s):
    """Escape plain-text data fields (sources, questions, names)."""
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def fr_date(iso):
    if not iso:
        return None
    parts = str(iso).split("-")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return "%s %s" % (MONTHS[int(parts[1])], parts[0])
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    day = "1ᵉʳ" if d == 1 else str(d)
    return "%s %s %s" % (day, MONTHS[m], y)


def short_place(s):
    if not s:
        return s
    s = s.split(" (")[0]
    for cut in (", Galicie", ", district", ", Pas-de-Calais", ", France"):
        i = s.find(cut)
        if i > 0:
            s = s[:i]
    return s


def haversine_km(a, b):
    """Great-circle distance in km between (lat, lon) pairs."""
    lat1, lon1 = a
    lat2, lon2 = b
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = (math.sin(dphi / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlmb / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


class Tree:
    def __init__(self, data):
        self.data = data
        self.people = {p["id"]: p for p in data["people"]}
        self.unions = {u["id"]: u for u in data["unions"]}
        self.sources = {s["id"]: s for s in data["sources"]}
        self.R = data["meta"]["rendering"]
        # tout id qui est partenaire d'une union = un ancêtre (a sa propre carte de couple) ;
        # les enfants qui n'y figurent pas sont des collatéraux (frères/sœurs à afficher).
        self.partner_ids = {pid for u in data["unions"] for pid in u["partners"]}

    # ----- auto-generation fallbacks (used when a person has no display.*) ---
    def auto_meta(self, p):
        lines, ev = [], {e["type"]: e for e in p.get("events", [])}
        sex_e = "e" if p.get("sex") == "F" else ""
        b = ev.get("birth") or ev.get("baptism")
        if b and b.get("date"):
            prep = "en" if len(str(b["date"])) == 4 else "le"
            verb = "né%s" if b.get("type", "birth") == "birth" else "baptisé%s"
            lines.append((verb + " %s <span class=\"yr\">%s</span>")
                         % (sex_e, prep, fr_date(b["date"])))
        place = (b or {}).get("place")
        if place:
            lines.append(esc(short_place(place)))
        occ = ev.get("occupation")
        if occ and occ.get("value"):
            lines.append("<em>%s</em>" % esc(occ["value"]))
        d = ev.get("death")
        if d and d.get("date"):
            lines.append("† <span class=\"yr\">%s</span>" % fr_date(d["date"]))
        return "<br>".join(lines)

    def auto_role(self, p):
        u = self.unions.get((p.get("parents") or {}).get("unionId") or "")
        if u and u.get("children"):
            child = self.people.get(u["children"][0])
            if child:
                g = child["names"].get("given") or child["names"]["surname"]
                return ("Fille de " if p.get("sex") == "F" else "Fils de ") + esc(g)
        return ""

    def auto_src(self, p):
        seen, labels = set(), []
        for e in p.get("events", []):
            for sid in e.get("sources", []):
                lbl = self.sources.get(sid, {}).get("shortLabel")
                if lbl and lbl not in seen:
                    seen.add(lbl)
                    labels.append(esc(lbl))
        return " · ".join(labels[:3])

    def card_class(self, p):
        disp = p.get("display") or {}
        conf = disp.get("confidence")
        if not conf:
            conf = (p.get("parents") or {}).get("confidence") or "unknown"
            if conf == "unknown":
                for e in p.get("events", []):
                    if e.get("confidence") == "documented":
                        conf = "documented"
                        break
        return CONF_CLASS.get(conf, "unk")

    # ----- card + union rendering -------------------------------------------
    def person_card(self, pid, focal=False):
        p = self.people[pid]
        disp = p.get("display") or {}
        cls = "person focal" if focal else "person %s" % self.card_class(p)
        out = ['<div class="%s" data-pid="%s" tabindex="0">' % (cls, esc(pid))]
        # corps (haut) : portrait + nom + repères + rôle ; la source est épinglée en bas
        # pour que toutes les cartes partagent une hauteur unique sans « trou » disgracieux.
        out.append('<div class="p-body">')
        port = p.get("portrait")
        if port:
            out.append('<img class="cameo" src="%s" alt="%s">'
                       % (port["file"], esc(port.get("alt", ""))))
        given = p["names"].get("given") or "N."
        out.append('<p class="nm">%s %s</p>' % (esc(given), esc(p["names"]["surname"])))
        meta = disp.get("meta", self.auto_meta(p))
        if meta:
            out.append('<div class="meta">%s</div>' % meta)
        role = disp.get("role", self.auto_role(p))
        if role:
            out.append('<span class="role">%s</span>' % role)
        out.append('</div>')  # p-body
        src = disp.get("src", self.auto_src(p))
        if src:
            out.append('<span class="src">%s</span>' % src)
        out.append('</div>')
        return "".join(out)

    def collateral_sibs_for(self, pid):
        """Frères/sœurs d'UNE personne : les autres enfants de son union parentale qui ne
        se sont pas eux-mêmes mariés dans l'arbre. Rendus À CÔTÉ de la personne (même
        génération), du côté extérieur de son couple."""
        pu = (self.people.get(pid, {}).get("parents") or {}).get("unionId")
        if not pu or pu not in self.unions:
            return []
        return [c for c in self.unions[pu].get("children", [])
                if c != pid and c not in self.partner_ids and c in self.people]

    def sib_group_html(self, sibs, side, label=None):
        n_m = sum(1 for c in sibs if self.people[c].get("sex") == "M")
        n_f = len(sibs) - n_m
        if label:
            lbl = esc(label)
        elif n_m and n_f:
            lbl = "frères &amp; sœurs"
        elif n_f:
            lbl = "sœur" if n_f == 1 else "sœurs"
        else:
            lbl = "frère" if n_m == 1 else "frères"
        out = ['<div class="sib-group %s"><span class="sib-lbl">%s</span>' % (side, lbl)]
        for c in sibs:
            out.append(self.sibling_card(c))
        out.append('</div>')
        return "".join(out)

    def union_stack(self, uid):
        u = self.unions[uid]
        disp = u.get("display") or {}
        focal = disp.get("focal", False)
        partners = u["partners"]
        stack_cls = "stack ext" if u.get("tier") == "extended" else "stack"
        out = ['<div class="%s"><div class="union-row">' % stack_cls]
        # cousins « épinglés » par exception (treeCousin.besideUnion) → tout à gauche,
        # reliés par JS à la carte de leur parent collatéral (linkTo), pas à une union
        cousins = [p["id"] for p in self.data["people"]
                   if (p.get("treeCousin") or {}).get("besideUnion") == uid]
        if cousins:
            lbl = (self.people[cousins[0]].get("treeCousin") or {}).get("label", "cousin")
            out.append(self.sib_group_html(cousins, "left", label=lbl))
        # frères/sœurs du 1ᵉʳ partenaire → à sa gauche (côté extérieur)
        left_sibs = self.collateral_sibs_for(partners[0])
        if left_sibs:
            out.append(self.sib_group_html(left_sibs, "left"))
        out.append('<div class="union-core" data-uid="%s">' % esc(uid))
        if focal and len(partners) == 2:
            out.append('<div class="focal-band">')
            out.append(self.person_card(partners[0], focal=True))
            out.append('<div class="union-glyph" style="font-size:21px;">&#10086;</div>')
            out.append(self.person_card(partners[1], focal=True))
            out.append('</div>')
            mt = disp.get("marriageTag")
            if mt:
                out.append('<p class="marriage-tag">⚭ %s</p>' % mt)
        elif len(partners) == 2:
            out.append('<div class="couple">')
            out.append(self.person_card(partners[0]))
            out.append('<div class="union-glyph">⚭</div>')
            out.append(self.person_card(partners[1]))
            out.append('</div>')
            mt = disp.get("marriageTag")
            if mt:
                out.append('<p class="marriage-tag">⚭ %s</p>' % mt)
        else:
            out.append(self.person_card(partners[0]))
        out.append('</div>')  # union-core
        # frères/sœurs du 2ᵉ partenaire → à sa droite (côté extérieur)
        if len(partners) == 2:
            right_sibs = self.collateral_sibs_for(partners[1])
            if right_sibs:
                out.append(self.sib_group_html(right_sibs, "right"))
        out.append('</div></div>')  # union-row, stack
        return "".join(out)

    def sibling_card(self, pid):
        p = self.people[pid]
        disp = p.get("display") or {}
        ev = {e["type"]: e for e in p.get("events", [])}
        by = str(ev["birth"]["date"])[:4] if ev.get("birth") and ev["birth"].get("date") else ""
        dy = str(ev["death"]["date"])[:4] if ev.get("death") and ev["death"].get("date") else ""
        given = p["names"].get("given") or "N."
        out = ['<div class="person sib %s" data-pid="%s" tabindex="0">'
               % (self.card_class(p), esc(pid))]
        out.append('<p class="nm">%s %s</p>' % (esc(given), esc(p["names"]["surname"])))
        line = ""
        if by or dy:
            line = '<span class="yr">%s–%s</span>' % (by, dy)
        blob = (disp.get("role", "") or "") + " " + (p.get("notes", "") or "")
        if "Mort pour la France" in blob:
            line += '<span class="sib-tag">✝ Mort pour la France</span>'
        if disp.get("tag"):
            line += '<span class="sib-tag">%s</span>' % esc(disp["tag"])
        if line:
            out.append('<div class="meta">%s</div>' % line)
        out.append('</div>')
        return "".join(out)

    # ----- generations ------------------------------------------------------
    def generations(self):
        from collections import defaultdict, deque
        gens = defaultdict(list)
        seen, q = set(), deque([(self.R["rootUnionId"], 1)])
        while q:
            uid, g = q.popleft()
            if not uid or uid in seen or uid not in self.unions:
                continue
            seen.add(uid)
            gens[g].append(uid)
            for pid in self.unions[uid]["partners"]:
                puid = (self.people[pid].get("parents") or {}).get("unionId")
                if puid:
                    q.append((puid, g + 1))
        return gens

    @staticmethod
    def gen_label(n):
        if n == 1:
            return "Parents"
        if n == 2:
            return "Grands-parents"
        if n == 3:
            return "Arrière-grands-parents"
        term = AIEUL_TERMS.get(n)
        return ("%s · %dᵉ génération" % (term, n)) if term else ("%dᵉ génération" % n)

    def branches(self, gens):
        """Étiquette chaque union ancestrale selon la lignée à laquelle elle appartient :
        's0'/'s1' = les deux branches issues des grands-parents (ex. Jastrzębski vs Leclercq).
        Renvoie (branch_of{uid->tag}, branch_name{tag->surname})."""
        branch_of, branch_name = {}, {}
        g2 = gens.get(2, [])
        if not g2:
            return branch_of, branch_name
        for i, pid in enumerate(self.unions[g2[0]]["partners"][:2]):
            tag = "s%d" % i
            branch_name[tag] = self.people[pid]["names"]["surname"]
            start = (self.people.get(pid, {}).get("parents") or {}).get("unionId")
            stack = [start]
            while stack:
                u = stack.pop()
                if not u or u in branch_of or u not in self.unions:
                    continue
                branch_of[u] = tag
                for ppid in self.unions[u]["partners"]:
                    stack.append((self.people.get(ppid, {}).get("parents") or {}).get("unionId"))
        return branch_of, branch_name

    def tree_html(self):
        gens = self.generations()
        if not gens:
            return ""
        lo, hi = min(gens), max(gens)
        rendered = {u for uids in gens.values() for u in uids}
        branch_of, self._branch_name = self.branches(gens)
        out = ['<div class="tree-wrap" id="treeWrap">']
        out.append('<div class="tree-scroll" id="treeScroll">')
        out.append('<div class="tree" id="tree">')
        out.append('<svg class="tree-links" id="treeLinks" aria-hidden="true">'
                   '<path class="branch-s0" d=""></path><path class="branch-s1" d=""></path>'
                   '<path d=""></path></svg>')
        labels = []  # étiquettes rendues hors du scroll, positionnées par JS en face de leur rangée
        for g in range(hi, lo - 1, -1):
            uids = gens.get(g, [])
            if not uids:
                continue
            # ancêtres directs au centre (jamais déplacés) ; alliés répartis de part et
            # d'autre pour que le cœur reste visuellement l'axe de la génération suivante
            core = [u for u in uids if self.unions[u].get("tier") != "extended"]
            ext = [u for u in uids if self.unions[u].get("tier") == "extended"]
            left, right = ext[0::2], ext[1::2]
            n_ext = sum(len(self.unions[u]["partners"]) for u in ext)
            out.append('<div class="gen-row" data-gen="%d">' % g)
            out.append('<div class="ancestors">')
            for uid in list(reversed(left)):
                out.append(self.union_stack(uid))
            out.append('<div class="core-anchor">')
            for uid in core:
                out.append(self.union_stack(uid))
            out.append('</div>')
            for uid in right:
                out.append(self.union_stack(uid))
            out.append('</div>')  # ancestors
            out.append('</div>')  # gen-row
            lb = '<div class="gen-side" data-gen="%d"><p class="gen-label">%s</p>' % (g, self.gen_label(g))
            if n_ext:
                lb += ('<button class="gen-ext-btn" data-gen="%d" data-n="%d" aria-expanded="false">'
                       '＋ %d allié%s</button>' % (g, n_ext, n_ext, "s" if n_ext > 1 else ""))
            labels.append(lb + '</div>')
        out.append('</div>')  # tree
        out.append('</div>')  # tree-scroll
        out.append('<div class="gen-labels" id="genLabels">%s</div>' % "".join(labels))
        out.append('</div>')  # tree-wrap
        out.append('<p class="continues">%s</p>' % self.R.get("continues", ""))
        # filiation links : [enfant (personne), union-parent, classe-lignée].
        # On relie chaque couple de parents à LEUR enfant précis (la personne), pas au
        # centre du couple de l'enfant — sinon on ne sait plus qui descend de qui.
        # Les frères/sœurs collatéraux sont inclus : ils forkent du même couple parent.
        rendered_persons = []
        seen = set()
        for U in rendered:
            for pid in self.unions[U]["partners"]:
                for c in [pid] + self.collateral_sibs_for(pid):
                    if c not in seen:
                        seen.add(c)
                        rendered_persons.append(c)
        links = []
        for pid in rendered_persons:
            pu = (self.people.get(pid, {}).get("parents") or {}).get("unionId")
            if pu and pu in rendered:
                links.append([pid, pu, branch_of.get(pu, "")])
        # cousins épinglés (treeCousin) : lien personne -> personne (carte du parent
        # collatéral), coloré comme la lignée dont ce parent descend
        for p in self.data["people"]:
            tc = p.get("treeCousin") or {}
            target = tc.get("linkTo")
            if not target or tc.get("besideUnion") not in rendered:
                continue
            tpu = (self.people.get(target, {}).get("parents") or {}).get("unionId")
            links.append([p["id"], target, branch_of.get(tpu, "")])
        out.append('<script>var FATREE=%s;</script>'
                   % json.dumps({"links": links}, ensure_ascii=False))
        return "\n".join(out)

    # ----- panels + gallery -------------------------------------------------
    @staticmethod
    def is_image_file(f):
        return bool(f) and f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))

    # regroupement des sources par famille de documents (catégories repliables)
    SRC_CATEGORIES = [
        ("census", "Recensements"),
        ("civil-record", "Actes d'état civil"),
        ("parish-record", "Registres paroissiaux"),
        ("military-record", "Registres militaires"),
        ("migration", "Émigration & identité"),
        ("land-record", "Cadastre & biens"),
        ("doleances", "Cahiers de doléances — 1789"),
        ("press-index", "Presse & bases en ligne"),
        ("compiled", "Arbres & compilations"),
        ("other", "Autres documents"),
    ]
    SRC_TYPE_TO_CAT = {
        "census": "census",
        "civil-record": "civil-record",
        "parish-record": "parish-record",
        "military-record": "military-record",
        "passport": "migration", "identity-document": "migration",
        "land-record": "land-record",
        "assembly-record": "doleances",
        "press": "press-index", "index-database": "press-index",
        "family-tree": "compiled", "compiled-tree": "compiled",
        "compiled-document": "compiled",
    }

    @staticmethod
    def source_sort_key(s):
        """Clé de tri chronologique d'une source : eventDate si présent, sinon
        première année plausible trouvée dans les métadonnées ; les pièces sans
        date repérable sont renvoyées en fin de catégorie."""
        d = s.get("eventDate")
        if d:
            parts = str(d).split("-")
            y = parts[0].zfill(4)
            m = (parts[1] if len(parts) > 1 else "00").zfill(2)
            day = (parts[2] if len(parts) > 2 else "00").zfill(2)
            return (0, "%s-%s-%s" % (y, m, day))
        text = " ".join(str(s.get(k, "")) for k in
                        ("coverage", "citation", "title", "shortLabel", "note"))
        mm = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", text)
        if mm:
            return (0, "%s-00-00" % mm.group(1))
        return (1, "9999-99-99")

    def source_concerns_index(self):
        """Index inversé : id de source -> « qui est concerné et pourquoi »,
        déduit des événements (personnes et unions) qui citent la source.
        Un champ manuel `concerns` sur la source prend le pas sur l'auto."""
        if getattr(self, "_concerns_idx", None) is not None:
            return self._concerns_idx
        idx = {}

        def add(sid, name, what):
            idx.setdefault(sid, {}).setdefault(name, [])
            if what and what not in idx[sid][name]:
                idx[sid][name].append(what)

        for p in self.data["people"]:
            nm = ((p["names"].get("given") or "") + " " + p["names"]["surname"]).strip()
            for e in p.get("events", []):
                lab = EVENT_LABELS.get(e.get("type"), e.get("type") or "").lower()
                for sid in e.get("sources", []):
                    add(sid, nm, lab)
        for u in self.data["unions"]:
            if not u["partners"]:
                continue
            names = " × ".join(self.full_name(x) for x in u["partners"])
            for e in u.get("events", []):
                if e.get("type") == "marriage":
                    for sid in e.get("sources", []):
                        add(sid, names, "mariage")
        self._concerns_idx = {
            sid: [(nm, whats) for nm, whats in people.items()]
            for sid, people in idx.items()
        }
        return self._concerns_idx

    def source_concerns_text(self, s):
        manual = s.get("concerns")
        if manual:
            return manual
        parts = self.source_concerns_index().get(s["id"])
        if not parts:
            return ""
        MAXP = 4
        chunks = ["%s (%s)" % (nm, ", ".join(whats)) for nm, whats in parts[:MAXP]]
        more = len(parts) - MAXP
        if more > 0:
            chunks.append("et %d autre%s" % (more, "s" if more > 1 else ""))
        return "Concerne %s." % " · ".join(chunks)

    def source_li(self, s):
        detail = "; ".join(x for x in (s.get("repository"), s.get("citation"),
                                       s.get("coverage")) if x)
        f = s.get("file")
        href = f if (f and f.startswith("http")) else (quote(f) if f else "")
        if f and self.is_image_file(f):
            # scan d'origine -> ouverture en popup (lightbox) + téléchargement
            name = ('<a class="doc-name doc-img" href="%s" data-cap="%s">%s</a>'
                    % (esc(href), esc(s["title"]), esc(s["title"])))
        elif f:
            # lien externe (URL Geneteka) ou PDF -> nouvel onglet
            name = ('<a class="doc-name" href="%s" target="_blank" rel="noopener">%s</a>'
                    % (esc(href), esc(s["title"])))
        else:
            name = '<span class="doc-name">%s</span>' % esc(s["title"])
        flag = ('<span class="doc-transflag">✎ transcription</span>'
                if s.get("transcription") else "")
        nviews = 1 + len([a for a in (s.get("annexes") or [])
                          if self.is_image_file(a.get("file"))]) if f and self.is_image_file(f) else 0
        views = ('<span class="doc-transflag">🖽 %d vues</span>' % nviews) if nviews > 1 else ""
        who = self.source_concerns_text(s)
        who_html = ('<span class="doc-concerns">%s</span>' % esc(who)) if who else ""
        return '<li>%s%s%s — %s.%s</li>' % (name, flag, views, esc(detail), who_html)

    def sources_panel(self):
        groups = {}
        for s in self.data["sources"]:
            cat = self.SRC_TYPE_TO_CAT.get(s.get("type"), "other")
            groups.setdefault(cat, []).append(s)
        blocks = []
        for key, label in self.SRC_CATEGORIES:
            items = groups.get(key)
            if not items:
                continue
            items = sorted(items, key=self.source_sort_key)
            lis = "\n".join(self.source_li(s) for s in items)
            trans = sum(1 for s in items if s.get("transcription"))
            meta = ('<span class="src-cat-meta">%d ✎</span>' % trans) if trans else ""
            blocks.append(
                '<details class="src-cat">\n'
                '<summary><span class="src-cat-name">%s</span>%s'
                '<span class="src-cat-count">%d</span></summary>\n'
                '<ul>\n%s\n</ul>\n</details>' % (esc(label), meta, len(items), lis))
        total = len(self.data["sources"])
        return ('<div class="panel">\n<h2>Sources utilisées</h2>\n'
                '<p class="src-intro">%d documents classés par type — '
                'cliquez une catégorie pour la déployer.</p>\n%s\n</div>'
                % (total, "\n".join(blocks)))

    def surname_panel(self):
        """Panneau « histoire d'une graphie » : frise des attestations du nom
        (le Clercq → Leclercq) + signature autographe de 1789 en illustration."""
        sh = self.data.get("surnameHistory")
        if not sh:
            return ""
        rows = []
        for a in sh.get("attestations", []):
            cls = "joined" if a.get("joined") else "sep"
            tag = "soudé" if a.get("joined") else "2 mots"
            rows.append(
                '<tr><td class="nh-yr">%s</td>'
                '<td><span class="nh-form %s">« %s »</span>'
                '<span class="nh-tag %s">%s</span><br>'
                '<span class="nh-doc">%s</span></td></tr>'
                % (esc(a["year"]), cls, esc(a["form"]), cls, tag, esc(a["doc"])))
        sig = sh.get("signature")
        fig = ""
        if sig:
            full = sig.get("full", sig["file"])
            href = quote(full) if not full.startswith("http") else full
            fig = ('<figure class="nh-sig">'
                   '<a class="doc-img" href="%s" data-cap="%s">'
                   '<img src="%s" alt="%s"></a>'
                   '<figcaption>%s</figcaption></figure>'
                   % (esc(href), esc(sig.get("caption", "")), esc(quote(sig["file"])),
                      esc(sig.get("alt", "")), esc(sig.get("caption", ""))))
        paras = "\n".join('<p class="nh-p">%s</p>' % p for p in sh.get("paragraphs", []))
        return ('<div class="panel name-hist">\n<h2>%s</h2>\n'
                '<p class="nh-intro">%s</p>\n'
                '<div class="nh-flex">\n<table class="nh-table">%s</table>\n%s\n</div>\n'
                '%s\n</div>'
                % (esc(sh["title"]), esc(sh.get("intro", "")), "".join(rows), fig, paras))

    def research_panel(self):
        qs = sorted(self.data.get("researchQuestions", []),
                    key=lambda q: PRIORITY.get(q.get("priority"), 9))
        lis = ['<li><b>%s</b> %s</li>' % (esc(q["question"]), esc(q.get("rationale", "")))
               for q in qs]
        return ("<div class=\"panel q\">\n<h2>À retrouver — prochaines pistes</h2>\n<ul>\n%s\n</ul>\n</div>"
                % "\n".join(lis))

    def gallery_html(self):
        g = self.data.get("gallery")
        if not g:
            return ""
        figs = []
        for it in g["items"]:
            figs.append(
                '<figure>\n<img src="%s" alt="%s" data-full="%s" data-cap="%s">\n'
                '<figcaption>%s\n<span class="cap-note">%s</span></figcaption>\n</figure>'
                % (it["file"], esc(it.get("alt", "")), it.get("full", it["file"]),
                   it.get("caption", ""), it.get("caption", ""), it.get("note", "")))
        return ('<div class="gallery">\n<h2 class="gallery-title">%s</h2>\n'
                '<p class="gallery-sub">%s</p>\n<div class="gallery-grid">\n%s\n</div>\n</div>'
                % (esc(g["title"]), esc(g.get("subtitle", "")), "\n".join(figs)))

    def lightbox_html(self):
        has_img_src = any(self.is_image_file(s.get("file")) for s in self.data["sources"])
        if not self.data.get("gallery") and not has_img_src:
            return ""
        # Table des documents, indexée par l'URL du scan principal (= href des liens de source).
        # Contient la transcription et la liste des vues (image principale + annexes).
        docs = {}
        for s in self.data["sources"]:
            f = s.get("file")
            if not (f and self.is_image_file(f)):
                continue
            annexes = [a for a in (s.get("annexes") or [])
                       if self.is_image_file(a.get("file"))]
            if not s.get("transcription") and not annexes:
                continue
            imgs = [{"u": quote(f), "c": s.get("title", "")}]
            for a in annexes:
                imgs.append({"u": quote(a["file"]), "c": a.get("caption", "")})
            docs[quote(f)] = {"t": s.get("transcription", ""), "d": s.get("title", ""),
                              "o": s.get("transcriptionOriginal", ""),
                              "n": s.get("transcriptionNote", ""), "imgs": imgs}
        return (
            '<div class="lb-backdrop" id="lb" aria-hidden="true">\n'
            '<span class="lb-close" id="lbClose" role="button" aria-label="Fermer">×</span>\n'
            '<div class="lb-stage" id="lbStage">\n'
            '<figure class="lb-figure"><img id="lbImg" src="" alt="">'
            '<div class="lb-thumbs" id="lbThumbs" hidden></div>'
            '<figcaption class="lb-cap" id="lbCap"></figcaption>'
            '<a class="lb-dl" id="lbDl" href="" download>⤓ Télécharger</a></figure>\n'
            '<aside class="lb-trans" id="lbTrans" hidden>'
            '<h3>Transcription</h3>'
            '<p class="lb-trans-doc" id="lbTransDoc"></p>'
            '<div class="lb-trans-tabs" id="lbTransTabs" hidden>'
            '<button type="button" id="lbTabMod" class="active">Modernisé</button>'
            '<button type="button" id="lbTabOrig">Texte d\'époque</button></div>'
            '<div class="lb-trans-body" id="lbTransBody"></div>'
            '<p class="lb-trans-note" id="lbTransNote"></p></aside>\n'
            '</div>\n'
            '</div>\n'
            '<script>\n'
            '(function(){\n'
            '  var FADOCS=' + json.dumps(docs, ensure_ascii=False) + ';\n'
            '  var lb=document.getElementById("lb"),img=document.getElementById("lbImg"),\n'
            '      cap=document.getElementById("lbCap"),dl=document.getElementById("lbDl"),\n'
            '      thumbs=document.getElementById("lbThumbs"),\n'
            '      stage=document.getElementById("lbStage"),tr=document.getElementById("lbTrans"),\n'
            '      trDoc=document.getElementById("lbTransDoc"),trBody=document.getElementById("lbTransBody"),\n'
            '      trNote=document.getElementById("lbTransNote"),\n'
            '      trTabs=document.getElementById("lbTransTabs"),\n'
            '      tabMod=document.getElementById("lbTabMod"),tabOrig=document.getElementById("lbTabOrig"),\n'
            '      curDoc=null;\n'
            '  function setTrans(orig){ if(!curDoc) return;\n'
            '    trBody.textContent=orig?curDoc.o:curDoc.t;\n'
            '    tabMod.classList.toggle("active",!orig); tabOrig.classList.toggle("active",!!orig);\n'
            '    tr.scrollTop=0; }\n'
            '  tabMod.addEventListener("click",function(){setTrans(false);});\n'
            '  tabOrig.addEventListener("click",function(){setTrans(true);});\n'
            '  function setImg(u,c){ img.src=u; img.alt=c||""; cap.innerHTML=c||""; dl.href=u; dl.setAttribute("download",""); }\n'
            '  function show(src,alt,c){\n'
            '    var d=FADOCS[src]||FADOCS[decodeURIComponent(src)];\n'
            '    thumbs.innerHTML="";\n'
            '    var imgs=d&&d.imgs;\n'
            '    if(imgs&&imgs.length>1){\n'
            '      imgs.forEach(function(im,i){ var t=document.createElement("img");\n'
            '        t.src=im.u; t.alt=im.c||""; t.title=im.c||""; if(i===0)t.className="active";\n'
            '        t.addEventListener("click",function(){ setImg(im.u,im.c);\n'
            '          Array.prototype.forEach.call(thumbs.children,function(x){x.classList.remove("active");}); t.classList.add("active"); });\n'
            '        thumbs.appendChild(t); });\n'
            '      thumbs.hidden=false;\n'
            '    } else { thumbs.hidden=true; }\n'
            '    if(imgs&&imgs.length){ setImg(imgs[0].u, imgs[0].c); } else { setImg(src, c); }\n'
            '    if(d&&d.t){ trDoc.textContent=d.d||""; curDoc=d;\n'
            '      if(d.o){ trTabs.hidden=false; setTrans(false); }\n'
            '      else { trTabs.hidden=true; trBody.textContent=d.t||""; }\n'
            '      trNote.textContent=d.n||""; trNote.style.display=d.n?"":"none";\n'
            '      tr.hidden=false; stage.classList.add("has-trans"); tr.scrollTop=0; }\n'
            '    else { tr.hidden=true; stage.classList.remove("has-trans"); }\n'
            '    lb.classList.add("open");lb.setAttribute("aria-hidden","false");}\n'
            '  function hide(){lb.classList.remove("open");lb.setAttribute("aria-hidden","true");img.src="";}\n'
            '  window.faShowImage=show;\n'
            '  document.querySelectorAll(".gallery figure img").forEach(function(im){\n'
            '    im.addEventListener("click",function(){show(im.getAttribute("data-full")||im.src, im.alt, im.getAttribute("data-cap"));});\n'
            '  });\n'
            '  document.querySelectorAll("a.doc-img").forEach(function(a){\n'
            '    a.addEventListener("click",function(e){ e.preventDefault();\n'
            '      show(a.getAttribute("href"), a.textContent, a.getAttribute("data-cap")); });\n'
            '  });\n'
            '  lb.addEventListener("click",function(e){ if(e.target===lb) hide(); });\n'
            '  document.getElementById("lbClose").addEventListener("click",hide);\n'
            '  document.addEventListener("keydown",function(e){ if(e.key==="Escape") hide(); });\n'
            '})();\n'
            '</script>')

    # ----- person detail modal ----------------------------------------------
    def full_name(self, pid):
        p = self.people.get(pid)
        if not p:
            return "?"
        return ((p["names"].get("given") or "N.") + " " + p["names"]["surname"]).strip()

    def person_detail(self, pid):
        p = self.people[pid]
        disp = p.get("display") or {}
        nm = self.full_name(pid)
        married = p["names"].get("marriedSurname")
        sub = ""
        if married and married != p["names"]["surname"]:
            sub = "épouse %s" % esc(married)
        var = [v for v in p["names"].get("variants", []) if v]
        if var:
            sub = (sub + " · " if sub else "") + "aussi : " + esc(" / ".join(var))
        # life events -> structured {l, v, n}
        evs, srcids = [], []
        for e in p.get("events", []):
            t = e.get("type")
            lab = EVENT_LABELS.get(t, (t or "").capitalize())
            if t in ("birth", "baptism", "death"):
                bits = []
                if e.get("date"):
                    bits.append('<span class="yr">%s</span>' % esc(fr_date(e["date"])))
                if e.get("place"):
                    bits.append(esc(short_place(e["place"])))
                v = " · ".join(bits)
            else:
                v = esc(e.get("value", "")) or (esc(short_place(e.get("place", ""))) if e.get("place") else "")
            evs.append({"l": lab, "v": v, "n": esc(e.get("note", ""))})
            srcids += e.get("sources", [])
        # family : parents + unions(spouse, marriage, children)
        parents = ""
        puid = (p.get("parents") or {}).get("unionId")
        if puid and puid in self.unions:
            parents = " &amp; ".join(esc(self.full_name(x)) for x in self.unions[puid]["partners"])
        fam = []
        for u in self.data["unions"]:
            if pid in u["partners"]:
                spouse = [self.full_name(x) for x in u["partners"] if x != pid]
                mev = next((e for e in u.get("events", []) if e.get("type") == "marriage"), None)
                line = ""
                if spouse:
                    line = "× <b>%s</b>" % esc(spouse[0])
                if mev:
                    md = fr_date(mev.get("date")) if mev.get("date") else ""
                    mp = short_place(mev.get("place")) if mev.get("place") else ""
                    tail = " · ".join(x for x in (md, mp) if x)
                    if tail:
                        line += (" — " if line else "Mariage ") + esc(tail)
                kids = [self.full_name(x) for x in u.get("children", [])]
                if kids:
                    line += '<span class="kids"><br>enfant(s) : %s</span>' % esc(", ".join(kids))
                if line:
                    fam.append(line)
        # sources (uniques, dans l'ordre d'apparition)
        srcs, seen = [], set()
        for sid in srcids:
            s = self.sources.get(sid)
            if not s or sid in seen:
                continue
            seen.add(sid)
            f = s.get("file")
            href = f if (f and f.startswith("http")) else (quote(f) if f else "")
            srcs.append({"label": esc(s.get("shortLabel") or s["title"]),
                         "href": href, "img": bool(f and self.is_image_file(f))})
        # descendance d'un collatéral (branche non prolongée dans l'arbre ascendant)
        desc = ""
        dd = p.get("descendants")
        if dd:
            rows = []
            for c in dd.get("children", []):
                yr = fr_date(c["date"]) if c.get("date") else ""
                rows.append('<div class="pd-desc-row"><span class="pd-desc-n">%s</span>'
                            '<span class="pd-desc-d">%s</span></div>'
                            % (esc(c["name"]), esc(yr)))
            head = ('<p class="pd-desc-sp">× <b>%s</b></p>' % esc(dd["spouse"])) if dd.get("spouse") else ""
            foot = ('<p class="pd-desc-note">%s</p>' % esc(dd["note"])) if dd.get("note") else ""
            desc = head + "".join(rows) + foot
        port = p.get("portrait")
        return {
            "name": esc(nm), "sub": sub, "desc": desc,
            "conf": CONF_LABEL.get(disp.get("confidence") or "", ""),
            "cls": self.card_class(p),
            "role": disp.get("role", self.auto_role(p)) or "",
            "portrait": (quote(port["file"]) if port else ""),
            "given": esc(p["names"].get("given") or p["names"].get("surname") or ""),
            "photoAlt": esc((port or {}).get("alt", "")),
            "events": evs, "parents": parents, "unions": fam,
            "notes": esc(p.get("notes", "")), "sources": srcs,
        }

    def person_modal_html(self):
        data = {pid: self.person_detail(pid) for pid in self.people}
        modal = (
            '<div class="pcard-backdrop" id="pcard" aria-hidden="true">\n'
            '<div class="pcard" id="pcardBox" role="dialog" aria-modal="true">\n'
            '<button class="pcard-close" id="pcardClose" aria-label="Fermer">×</button>\n'
            '<div class="pcard-head">'
            '<div><span class="pcard-conf" id="pcConf"></span>'
            '<h3 class="pcard-name" id="pcName"></h3>'
            '<p class="pcard-role" id="pcRole"></p></div></div>\n'
            '<div id="pcBody"></div>\n</div>\n</div>\n')
        js = (
            '<script>\n'
            'var FAPEOPLE=' + json.dumps(data, ensure_ascii=False) + ';\n'
            '(function(){\n'
            '  var bk=document.getElementById("pcard"),box=document.getElementById("pcardBox"),\n'
            '      body=document.getElementById("pcBody"),nameEl=document.getElementById("pcName"),\n'
            '      roleEl=document.getElementById("pcRole"),confEl=document.getElementById("pcConf");\n'
            '  function sec(title,inner){ return inner ? \'<div class="pcard-sec"><h4>\'+title+\'</h4>\'+inner+\'</div>\' : ""; }\n'
            '  function open(pid){ var d=FAPEOPLE[pid]; if(!d) return;\n'
            '    box.className="pcard "+(d.cls||"");\n'
            '    nameEl.innerHTML=d.name+(d.sub?\'<small>\'+d.sub+\'</small>\':"");\n'
            '    roleEl.innerHTML=d.role||""; confEl.textContent=d.conf||"";\n'
            '    var photo=d.portrait ? \'<img class="pcard-photo" src="\'+d.portrait+\'" alt="\'+(d.photoAlt||("Photo de "+d.given))+\'">\'+(d.photoAlt?\'<span class="pcard-photo-cap">\'+d.photoAlt+\'</span>\':"") : "";\n'
            '    var vie=(d.events||[]).map(function(e){ return \'<div class="pd-ev"><span class="pd-l">\'+e.l+\'</span><span class="pd-v">\'+e.v+(e.n?\'<span class="pd-n">\'+e.n+\'</span>\':"")+\'</span></div>\'; }).join("");\n'
            '    var fam=""; if(d.parents) fam+=\'<div class="pcard-fam">Enfant de <b>\'+d.parents+\'</b></div>\';\n'
            '    (d.unions||[]).forEach(function(u){ fam+=\'<div class="pcard-fam" style="margin-top:7px;">\'+u+\'</div>\'; });\n'
            '    var src=(d.sources||[]).map(function(s){ var mk=s.img?\'⌕\':\'↗\';\n'
            '      return \'<a href="\'+s.href+\'" data-img="\'+(s.img?1:0)+\'">\'+s.label+\' <span class="mk">\'+mk+\'</span></a>\'; }).join("");\n'
            '    body.innerHTML=sec("Photo de "+d.given,photo)+sec("Repères de vie",vie)+sec("Famille",fam)+sec("Descendance",d.desc)+sec("Notes",d.notes?\'<p class="pcard-notes">\'+d.notes+\'</p>\':"")+sec("Sources",src?\'<div class="pcard-src">\'+src+\'</div>\':"");\n'
            '    var ph=body.querySelector(".pcard-photo"); if(ph&&window.faShowImage){ ph.addEventListener("click",function(){ window.faShowImage(d.portrait, "Photo de "+d.given, d.photoAlt||("Photo de "+d.given)); }); }\n'
            '    body.querySelectorAll(".pcard-src a").forEach(function(a){ a.addEventListener("click",function(e){ e.preventDefault();\n'
            '      if(a.getAttribute("data-img")==="1" && window.faShowImage){ window.faShowImage(a.getAttribute("href"), a.textContent, a.textContent); }\n'
            '      else { window.open(a.getAttribute("href"),"_blank","noopener"); } }); });\n'
            '    bk.classList.add("open"); bk.setAttribute("aria-hidden","false"); box.scrollTop=0; }\n'
            '  function close(){ bk.classList.remove("open"); bk.setAttribute("aria-hidden","true"); }\n'
            '  document.addEventListener("click",function(e){ var c=e.target.closest&&e.target.closest(".person"); \n'
            '    if(c && c.getAttribute("data-pid")){ open(c.getAttribute("data-pid")); } });\n'
            '  document.addEventListener("keydown",function(e){ var c=document.activeElement;\n'
            '    if(e.key==="Enter" && c && c.classList && c.classList.contains("person")){ open(c.getAttribute("data-pid")); }\n'
            '    if(e.key==="Escape" && bk.classList.contains("open")) close(); });\n'
            '  document.getElementById("pcardClose").addEventListener("click",close);\n'
            '  bk.addEventListener("click",function(e){ if(e.target===bk) close(); });\n'
            '})();\n'
            '</script>')
        return modal + js

    # ----- map (events aggregated by place) ---------------------------------
    def map_data(self):
        places = self.data.get("places", {})
        if not places:
            return {"places": [], "migration": []}
        agg = {k: [] for k in places}

        def match(text):
            if not text:
                return None
            t = text.lower()
            for k, pl in places.items():
                for a in pl.get("aliases", []):
                    if a.lower() in t:
                        return k
            return None

        LABELS = {"birth": "naissance", "baptism": "baptême",
                  "death": "décès", "residence": "résidence"}

        def line(name, label, y):
            tail = ' <span class="yr">%s</span>' % y if y else ""
            return "%s — %s%s" % (esc(name), label, tail)

        ext_people = {p["id"] for p in self.data["people"] if p.get("tier") == "extended"}
        for p in self.data["people"]:
            if p.get("tier") == "extended":
                continue  # familles alliées : hors carte (arbre trop dense)
            nm = (p["names"].get("given") or "N.") + " " + p["names"]["surname"]
            for ev in p.get("events", []):
                if ev.get("type") == "marriage":
                    continue
                lab = LABELS.get(ev.get("type"))
                if not lab:
                    continue
                k = match(ev.get("place"))
                if not k:
                    continue
                y = str(ev["date"])[:4] if ev.get("date") else ""
                agg[k].append((int(y) if y else 9999, line(nm, lab, y)))
        for u in self.data["unions"]:
            if u.get("tier") == "extended":
                continue
            for ev in u.get("events", []):
                if ev.get("type") != "marriage":
                    continue
                k = match(ev.get("place"))
                if not k:
                    continue
                names = " × ".join(
                    (self.people[pid]["names"].get("given") or self.people[pid]["names"]["surname"])
                    for pid in u["partners"])
                y = str(ev["date"])[:4] if ev.get("date") else ""
                agg[k].append((int(y) if y else 9999, line(names, "mariage", y)))

        out = []
        for k, pl in places.items():
            evs = sorted(agg[k], key=lambda x: x[0])
            if not evs:
                continue
            out.append({"key": k, "name": pl["name"], "detail": pl.get("detail", ""),
                        "region": pl.get("region", ""),
                        "lat": pl["lat"], "lon": pl["lon"], "events": [e[1] for e in evs]})
        keys = {p["key"] for p in out}
        migration = []
        for s in self.R.get("migration", []):
            if s[0] in keys and s[1] in keys:
                a, b = places[s[0]], places[s[1]]
                km = int(round(haversine_km((a["lat"], a["lon"]), (b["lat"], b["lon"])) / 5.0) * 5)
                label = "≈ %s km" % "{:,}".format(km).replace(",", " ")
                migration.append({"from": s[0], "to": s[1], "label": label})
        # régions présentes (dans l'ordre de déclaration), pour les puces et les bulles de cluster
        used = {p["region"] for p in out if p.get("region")}
        regdefs = (self.R.get("map", {}) or {}).get("regions", {}) or {}
        regions = [{"key": rk, "name": rdef.get("name", rk), "detail": rdef.get("detail", "")}
                   for rk, rdef in regdefs.items() if rk in used]
        # route d'émigration (reconstitution historique) : étapes ordonnées + distances
        route = None
        er = self.R.get("emigrationRoute")
        if er and er.get("waypoints"):
            wps = er["waypoints"]
            for i, w in enumerate(wps):
                w = dict(w)
                w["step"] = i + 1
                wps[i] = w
            segs = []
            for a, b in zip(wps, wps[1:]):
                km = int(round(haversine_km((a["lat"], a["lon"]), (b["lat"], b["lon"])) / 5.0) * 5)
                segs.append({"from": [a["lat"], a["lon"]], "to": [b["lat"], b["lon"]],
                             "label": "≈ %s km" % "{:,}".format(km).replace(",", " ")})
            total_km = 0
            for a, b in zip(wps, wps[1:]):
                total_km += haversine_km((a["lat"], a["lon"]), (b["lat"], b["lon"]))
            route = {"title": er.get("title", "Route d'émigration"),
                     "period": er.get("period", ""), "intro": er.get("intro", ""),
                     "waypoints": wps, "segments": segs,
                     "total": "≈ %s km" % "{:,}".format(int(round(total_km / 10.0) * 10)).replace(",", " ")}
        return {"places": out, "migration": migration, "regions": regions, "route": route}

    def map_html(self):
        data = self.map_data()
        if not data["places"]:
            return ""
        m = self.R.get("map", {})
        chips = ['<div class="faregions" id="faRegions"><span class="fr-lead">Secteurs :</span>']
        for r in data.get("regions", []):
            chips.append('<button class="fareg-chip" data-reg="%s">%s</button>'
                         % (esc(r["key"]), esc(r["name"])))
        chips.append('<button class="fareg-chip" data-reg="_all">Vue d’ensemble</button>')
        route = data.get("route")
        if route:
            chips.append('<button class="fareg-chip fareg-route" id="faRouteBtn" '
                         'aria-pressed="true">✕ Route d’émigration 1929</button>')
        chips.append('</div>')
        chip_html = "".join(chips) if data.get("regions") else ""
        # encart narratif : la route type des mineurs polonais
        route_html = ""
        if route:
            steps = []
            for w in route["waypoints"]:
                steps.append(
                    '<li><span class="rt-step">%d</span><div><span class="rt-name">%s</span>'
                    '<span class="rt-detail">%s</span><p class="rt-note">%s</p></div></li>'
                    % (w["step"], esc(w["name"]), esc(w.get("detail", "")), esc(w.get("note", ""))))
            route_html = (
                '<div class="route-panel">\n'
                '<h3 class="route-title">' + esc(route["title"])
                + (' <span class="route-period">' + esc(route["period"]) + '</span>' if route.get("period") else "")
                + '</h3>\n'
                + ('<p class="route-intro">' + esc(route["intro"]) + '</p>\n' if route.get("intro") else "")
                + '<ol class="route-steps">\n' + "\n".join(steps) + '\n</ol>\n'
                + '<p class="route-total">Trajet total : <b>' + esc(route.get("total", "")) + '</b> '
                + '— reconstitution historique, non documentée pour cette famille.</p>\n</div>\n')
        return ('<div class="famap-section">\n<h2 class="map-title">' + esc(m.get("title", "Carte"))
                + '</h2>\n<p class="map-sub">' + esc(m.get("subtitle", "")) + '</p>\n'
                + chip_html + '\n'
                + '<div id="famap"></div>\n'
                + '<p class="map-fs-hint">⛶ plein écran · clic sur un secteur = zoom · survol d\'un lieu ou d\'une étape = détails</p>\n'
                + route_html
                + '</div>\n'
                + '<div class="mapfull-backdrop" id="mapfull">'
                + '<button class="mapfull-close" id="mapfullClose" aria-label="Fermer">×</button>'
                + '<div id="mapfull-holder"></div></div>\n'
                + '<script>var FAMAP=' + json.dumps(data, ensure_ascii=False) + ';</script>\n'
                + MAP_INIT_JS)

    # ----- whole document ---------------------------------------------------
    def render(self):
        R = self.R
        h = R.get("headline", {})
        foot = R.get("footer", [])
        body = []
        body.append('<body>')
        body.append('<div class="sheet">')
        body.append("""
  <header class="masthead">
    <p class="eyebrow">%s</p>
    <h1><span class="em">%s</span> <span class="amp">&amp;</span> <span class="em">%s</span></h1>
    <p class="route">%s</p>
    <div class="rule"></div>
  </header>""" % (esc(R.get("eyebrow", "")), esc(h.get("left", "")),
                  esc(h.get("right", "")), R.get("route", "")))
        body.append("""
  <div class="legend">
    <span><i class="chip doc"></i> Documenté — acte officiel</span>
    <span><i class="chip prob"></i> Probable — index Geneteka</span>
    <span><i class="chip fam"></i> Mémoire familiale</span>
    <span><i class="chip unk"></i> À retrouver</span>
  </div>""")
        n_ext = sum(1 for p in self.data["people"] if p.get("tier") == "extended")
        tree_markup = self.tree_html()  # peuple aussi self._branch_name
        bn = getattr(self, "_branch_name", {})
        if len(bn) == 2:
            body.append(
                '<div class="branch-legend">'
                '<span class="s0">lignée <b>%s</b></span>'
                '<span class="s1">lignée <b>%s</b></span>'
                '</div>' % (esc(bn.get("s0", "")), esc(bn.get("s1", ""))))
        body.append(tree_markup)
        if n_ext:
            # bouton global EN BAS de l'arbre (chaque génération a en plus son propre petit bouton)
            body.append(
                '<div class="tree-toggle"><button class="toggle-btn" id="showAllBtn" aria-expanded="false">'
                '<span class="tg-ic">⊕</span> Afficher toutes les familles alliées '
                '(Lesire, Léonard, Dufour…)</button></div>')
        body.append(TREE_JS)
        body.append(self.gallery_html())
        body.append(self.map_html())
        sp = self.surname_panel()
        if sp:
            body.append('<div style="margin-top:52px;">%s</div>' % sp)
        body.append('<div style="margin-top:52px;">%s</div>' % self.sources_panel())
        body.append("""
  <footer>
    <span class="seal">&#10086;</span>
    %s
  </footer>""" % "<br>\n    ".join(esc(line) for line in foot))
        body.append('</div>')  # .sheet
        body.append(self.person_modal_html())
        body.append(self.lightbox_html())
        body.append('</body>')
        body.append('</html>')
        return HEAD + "\n".join(body) + "\n"


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    html = Tree(data).render()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("Généré : %s (%d caractères) depuis %s"
          % (os.path.basename(OUT_PATH), len(html), os.path.basename(DATA_PATH)))


if __name__ == "__main__":
    sys.exit(main())
