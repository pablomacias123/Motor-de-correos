# limpiar_facturas.py
from pathlib import Path
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import shutil
from tqdm import tqdm

# === CONFIGURACIÓN ===
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "FACTURAS DESCARGADAS"
OUT_DIR = BASE_DIR / "FACTURAS DESCARGADAS"  # sobrescribe las originales
ERR_DIR = BASE_DIR / "Errors"

for d in [SRC_DIR, OUT_DIR, ERR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === CONTADORES PARA EL RESUMEN ===
total_pdfs = 0
procesadas_walmart = 0
recortadas = 0
sin_cambios = 0
en_error = 0
no_total = 0
otras_facturas = 0

# === PROCESO PRINCIPAL ===
pdf_files = [p for p in SRC_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]

if not pdf_files:
    print("⚠️  No se encontraron archivos PDF en FACTURAS DESCARGADAS")
    exit()

print(f"🧹 Analizando y limpiando {len(pdf_files)} archivos PDF...\n")

for pdf_path in tqdm(pdf_files, desc="Limpiando facturas Walmart"):
    total_pdfs += 1
    try:
        # --- Detectar si es factura de Walmart ---
        is_walmart = "walmart" in pdf_path.name.lower()
        if not is_walmart:
            with pdfplumber.open(pdf_path) as pdf:
                text_first_page = pdf.pages[0].extract_text() or ""
                if "walmart" in text_first_page.lower():
                    is_walmart = True

        # Si no es de Walmart, no hacemos nada
        if not is_walmart:
            otras_facturas += 1
            continue

        procesadas_walmart += 1
        page_limit = None

        # --- Buscar la página con el TOTAL ---
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").lower()
                if "total" in text:
                    page_limit = i + 1  # Nos quedamos hasta esa página (1-index)
            num_paginas = len(pdf.pages)

        # --- Si no se encontró el total ---
        if not page_limit:
            no_total += 1
            print(f"⚠️  No se encontró 'TOTAL' en {pdf_path.name}, movido a Errors/")
            shutil.move(str(pdf_path), str(ERR_DIR / pdf_path.name))
            continue

        # --- Si hay páginas extra, recortar ---
        if page_limit < num_paginas:
            reader = PdfReader(str(pdf_path))
            writer = PdfWriter()

            for i in range(page_limit):
                writer.add_page(reader.pages[i])

            with open(pdf_path, "wb") as f:
                writer.write(f)

            recortadas += 1
            print(f"✅ {pdf_path.name}: recortado hasta la página {page_limit} (se eliminaron {num_paginas - page_limit})")

        else:
            sin_cambios += 1
            print(f"ℹ️  {pdf_path.name}: sin cambios ({num_paginas} páginas)")

    except Exception as e:
        en_error += 1
        print(f"❌ Error procesando {pdf_path.name}: {e}")
        shutil.move(str(pdf_path), str(ERR_DIR / pdf_path.name))

# === RESUMEN FINAL ===
print("\n📊 RESUMEN FINAL DE LIMPIEZA")
print("────────────────────────────────────────────")
print(f"Total de PDFs analizados:      {total_pdfs}")
print(f"Facturas Walmart procesadas:   {procesadas_walmart}")
print(f"Recortadas (con TOTAL):        {recortadas}")
print(f"Sin cambios (1 hoja útil):     {sin_cambios}")
print(f"No se encontró 'TOTAL':        {no_total}")
print(f"Movidas a Errors/:             {en_error}")
print(f"Otras facturas (sin tocar):    {otras_facturas}")
print("────────────────────────────────────────────")
print("🏁 Limpieza de facturas completada.")
