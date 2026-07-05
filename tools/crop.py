#!/usr/bin/env python3
"""Recadrage / zoom de scans pour la lecture OCR des manuscrits.

Ce Mac n'a ni ImageMagick ni Pillow système : on passe par le venv persistant
`tools/venv` (voir tools/README ou le skill `ingest-documents`).

Exemples
--------
# 1) Connaître les dimensions d'un scan avant de recadrer :
tools/venv/bin/python tools/crop.py "sources/Recensement1911Noyelles-sous-Lens.jpeg"

# 2) Recadrer une zone (coords en pixels de l'ORIGINAL) et agrandir ×2 :
tools/venv/bin/python tools/crop.py sources/xxx.jpg --box 2500 2050 4808 2850 --scale 2

# 3) Nom de rue en marge (texte tourné) : recadrer puis pivoter :
tools/venv/bin/python tools/crop.py sources/xxx.jpg --box 2560 1600 2860 3200 --rotate -90

Sortie par défaut : /tmp/crop.png (à ouvrir avec l'outil Read). Toujours affiché :
la taille de l'image et, après crop, la taille du résultat.
"""
import argparse
import sys

from PIL import Image


def main():
    ap = argparse.ArgumentParser(description="Recadre/zoome un scan pour la lecture.")
    ap.add_argument("image", help="chemin du scan (dans sources/ en général)")
    ap.add_argument("--box", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"),
                    help="rectangle à extraire, en pixels de l'original")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="facteur d'agrandissement du crop (ex. 2 pour ×2)")
    ap.add_argument("--rotate", type=float, default=0.0,
                    help="rotation en degrés (ex. -90 pour un texte de marge)")
    ap.add_argument("-o", "--out", default="/tmp/crop.png", help="fichier de sortie")
    args = ap.parse_args()

    im = Image.open(args.image)
    print("image %s : %dx%d" % (args.image, im.width, im.height))
    if not args.box:
        print("(aucun --box : dimensions affichées, rien d'écrit)")
        return

    x0, y0, x1, y1 = args.box
    x0, x1 = sorted((max(0, x0), min(im.width, x1)))
    y0, y1 = sorted((max(0, y0), min(im.height, y1)))
    if x1 - x0 < 2 or y1 - y0 < 2:
        sys.exit("boîte vide ou hors image après recadrage aux bornes du scan")

    crop = im.crop((x0, y0, x1, y1))
    if args.scale and args.scale != 1.0:
        crop = crop.resize((max(1, round(crop.width * args.scale)),
                            max(1, round(crop.height * args.scale))))
    if args.rotate:
        crop = crop.rotate(args.rotate, expand=True)
    crop.save(args.out)
    print("écrit %s : %dx%d" % (args.out, crop.width, crop.height))


if __name__ == "__main__":
    main()
