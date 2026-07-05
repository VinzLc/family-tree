# tools/

Outillage local pour l'intégration de documents (voir le skill `ingest-documents`).

- **`venv/`** — venv Python persistant avec Pillow (ce Mac n'a pas de Pillow
  système). Le recréer si absent : `python3 -m venv tools/venv && tools/venv/bin/pip install -q Pillow`
- **`crop.py`** — recadrage / zoom / rotation d'un scan pour la lecture OCR.
  `tools/venv/bin/python tools/crop.py <image> [--box X0 Y0 X1 Y1] [--scale N] [--rotate deg] [-o out.png]`
