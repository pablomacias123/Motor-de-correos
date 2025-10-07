# unir_facturas.py
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import shutil
from tqdm import tqdm
import time
import re

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent
IN_DIR = BASE_DIR / "FACTURAS INVERTIDAS"
OUT_DIR = BASE_DIR / "FACTURAS FINAL"
ERR_DIR = BASE_DIR / "Errors"

for d in [IN_DIR, OUT_DIR, ERR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === FUNCIÓN PARA OBTENER FECHA ===
def extract_date(filename):
    match = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", filename)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (0, 0, 0)

# === UNIÓN ===
files = [p for p in IN_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
if not files:
    print("⚠️  No hay archivos para unir en FACTURAS INVERTIDAS")
    exit()

# Orden descendente (más nueva → más vieja)
files = sorted(files, key=lambda p: extract_date(p.name), reverse=True)

timestamp = time.strftime("%Y%m%d_%H%M%S")
output_file = OUT_DIR / f"Facturas_unidas_{timestamp}.pdf"
writer = PdfWriter()

print(f"📎 Uniendo {len(files)} archivos PDF (más nueva → más vieja)...")

for pdf_path in tqdm(files, desc="Uniendo PDFs"):
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
    except Exception as e:
        print(f"❌ Error al unir {pdf_path.name}: {e}")
        shutil.move(str(pdf_path), str(ERR_DIR / pdf_path.name))

# Guardar resultado final
with output_file.open("wb") as f:
    writer.write(f)

print(f"✅ Archivo final creado: {output_file}")
