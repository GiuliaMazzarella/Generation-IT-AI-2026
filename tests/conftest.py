import sys
from pathlib import Path

# Aggiunge la root del progetto al sys.path per permettere import dei package locali
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
