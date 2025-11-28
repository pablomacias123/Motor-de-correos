from pathlib import Path
import pdfplumber
from pypdf import PdfReader, PdfWriter
import shutil
from tqdm import tqdm
import re

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "FACTURAS DESCARGADAS"
ERR_DIR = BASE_DIR / "Errors"

for d in [SRC_DIR, ERR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === CONTADORES ===
total_pdfs = 0
walmart_ok = 0
recortadas = 0
sin_cambios = 0
no_total = 0
otras = 0
errores = 0


# === DETECCIÓN ROBUSTA DE WALMART ===
def es_walmart(nombre, texto):
    nombre = nombre.lower()
    texto = (texto or "").lower()

    patrones = [
        "walmart",
        "wal mart",
        "wal-mart",
        "nwm",
        "nueva wal mart",
        "nueva wal-mart",
        "nueva walmart",
        "nueva wal-mart",
        "nueva wal mart de méxico",
        "nueva wal mart de mexico",
        "nueva wal-mart de mexico",
    ]

    rfc_oficial = "nwm9709244w4"  # WALMART RFC real

    return (
        any(p in nombre for p in patrones) or
        any(p in texto for p in patrones) or
        rfc_oficial in texto
    )


# === DETECCIÓN DE PÁGINA BASURA ===
def pagina_es_basura(text):
    if not text:
        return True

    t = text.lower().strip()

    if len(t) < 40:
        return True

    if "representación impresa" in t or "cfdi" in t:
        return True

    if re.fullmatch(r"p[aá]gina\s+\d+\s+de\s+\d+", t):
        return True

    return False


# === PROCESAR PDFs ===
pdf_files = [p for p in SRC_DIR.iterdir() if p.suffix.lower() == ".pdf"]

print(f"\n🧹 Analizando y limpiando {len(pdf_files)} archivos PDF...\n")

for pdf_path in tqdm(pdf_files, desc="Limpieza Walmart"):
    total_pdfs += 1

    try:
        # === Primera página para detección ===
        with pdfplumber.open(pdf_path) as pdf:
            first_text = (pdf.pages[0].extract_text() or "")

        # === Detectar Walmart ===
        if not es_walmart(pdf_path.name, first_text):
            otras += 1
            continue

        walmart_ok += 1

        # === Leer todas las páginas ===
        with pdfplumber.open(pdf_path) as pdf:

            num_pages = len(pdf.pages)
            page_limit = None

            # Buscar página con "TOTAL"
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").lower()

                if "total" in text or "total con letra" in text:
                    page_limit = i + 1
                    break

            if not page_limit:
                no_total += 1
                shutil.move(pdf_path, ERR_DIR / pdf_path.name)
                continue

            # Determinar si última página es basura
            last_text = (pdf.pages[-1].extract_text() or "")
            paginas_utiles = page_limit

            if num_pages > page_limit:
                if pagina_es_basura(last_text):
                    paginas_utiles = num_pages - 1

        # === Recortar con PYPDF ===
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()

        for i in range(paginas_utiles):
            writer.add_page(reader.pages[i])

        temp_out = pdf_path.with_suffix(".temp.pdf")
        with open(temp_out, "wb") as f:
            writer.write(f)

        shutil.move(temp_out, pdf_path)

        if paginas_utiles < num_pages:
            recortadas += 1
        else:
            sin_cambios += 1

    except Exception as e:
        errores += 1
        shutil.move(pdf_path, ERR_DIR / pdf_path.name)
        print(f"\n❌ Error en {pdf_path.name}: {e}")


# === RESUMEN ===
print("\n📊 RESUMEN FINAL")
print("────────────────────────────────────────────")
print(f"Total PDFs:                    {total_pdfs}")
print(f"Walmart detectados:            {walmart_ok}")
print(f"Recortados:                    {recortadas}")
print(f"Sin cambios:                   {sin_cambios}")
print(f"No se encontró TOTAL:          {no_total}")
print(f"Errores:                       {errores}")
print(f"No Walmart (sin tocar):        {otras}")
print("────────────────────────────────────────────")
print("🏁 Limpieza completa.")
