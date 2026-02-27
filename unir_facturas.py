from pathlib import Path
from pypdf import PdfReader, PdfWriter
import shutil
from tqdm import tqdm
import time
import re
import calendar

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent
IN_DIR = BASE_DIR / "FACTURAS INVERTIDAS"
OUT_DIR = BASE_DIR / "FACTURAS FINAL"
ERR_DIR = BASE_DIR / "Errors"

for d in [IN_DIR, OUT_DIR, ERR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === FUNCIÓN PARA OBTENER FECHA DESDE NOMBRE DE ARCHIVO ===
def extract_date(filename):
    match = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", filename)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (0, 0, 0)

# === LISTADO DE ARCHIVOS ===
files = [p for p in IN_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
if not files:
    print("  No hay archivos para unir en FACTURAS INVERTIDAS")
    exit()

# Orden descendente (más nueva → más vieja)
files = sorted(files, key=lambda p: extract_date(p.name), reverse=True)

# === FORMATO DE FECHA PARA ARCHIVO FINAL ===
fecha_actual = time.localtime()

dia = f"{fecha_actual.tm_mday:02d}"
mes = f"{fecha_actual.tm_mon:02d}"
anio = fecha_actual.tm_year

nombre_mes = calendar.month_name[fecha_actual.tm_mon]  # "January"
nombre_mes = nombre_mes.capitalize()

# Cambiar a nombre de mes en español (si quieres español 100%)
meses_es = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

nombre_mes = meses_es[fecha_actual.tm_mon]

nombre_salida = f"{dia}-{mes}-{anio}_{nombre_mes}.pdf"
output_file = OUT_DIR / nombre_salida

writer = PdfWriter()

print(f" Uniendo {len(files)} archivos PDF (más nueva → más vieja)...")

# === UNIÓN DE PDFs ===
for pdf_path in tqdm(files, desc="Uniendo PDFs"):
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
    except Exception as e:
        print(f" Error al unir {pdf_path.name}: {e}")
        shutil.move(str(pdf_path), str(ERR_DIR / pdf_path.name))

# === GUARDAR RESULTADO ===
with output_file.open("wb") as f:
    writer.write(f)

print(f" Archivo final creado: {output_file}\n")
