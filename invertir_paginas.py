# invertir_paginas.py
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import shutil
from tqdm import tqdm

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "FACTURAS DESCARGADAS"
OUT_DIR = BASE_DIR / "FACTURAS INVERTIDAS"
ERR_DIR = BASE_DIR / "Errors"

# Crear carpetas si no existen
for d in [SRC_DIR, OUT_DIR, ERR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === PROCESO ===
pdf_files = [p for p in SRC_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]

if not pdf_files:
    print("  No se encontraron PDFs en FACTURAS DESCARGADAS")
    exit()

print(f" Invirtiendo {len(pdf_files)} archivos PDF...")

for pdf_path in tqdm(pdf_files, desc="Invirtiendo páginas"):
    try:
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()

        # Invertir las páginas
        for page in reversed(reader.pages):
            writer.add_page(page)

        # Guardar el PDF invertido
        out_file = OUT_DIR / pdf_path.name
        with out_file.open("wb") as f:
            writer.write(f)

    except Exception as e:
        print(f" Error en {pdf_path.name}: {e}")
        # Mover a carpeta de errores
        shutil.move(str(pdf_path), str(ERR_DIR / pdf_path.name))

print(" Inversión completada.")