import re
from pathlib import Path
from datetime import datetime
import pdfplumber
from pypdf import PdfReader

# ====== RUTA FIJA ======
FACTURAS_DIR = Path(r"C:\Trabajo\Motor-de-correos\FACTURAS DESCARGADAS")

# Meses en español
MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

# Patrones con grupos claros para armar datetime sin ambigüedad
RX_ISO = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])[T ]([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b")
RX_YMD = re.compile(r"\b(20\d{2})[-/\.](0[1-9]|1[0-2])[-/\.](0[1-9]|[12]\d|3[01])\b")
RX_DMY = re.compile(r"\b(0[1-9]|[12]\d|3[01])[-/\.](0[1-9]|1[0-2])[-/\.](20\d{2})\b")
RX_ES  = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])\s+de\s+(enero|febrero|marzo|abril|mayo|junio|"
    r"julio|agosto|septiembre|octubre|noviembre|diciembre)\s+del\s+(20\d{2})"
    r"(?:\s+([01]?\d|2[0-3]):([0-5]\d):?([0-5]\d)?)?\b",
    re.IGNORECASE
)

def extract_text_pdf(pdf_path: Path, max_pages: int = 2) -> str:
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages[:max_pages])
    except Exception:
        try:
            reader = PdfReader(str(pdf_path))
            pages = min(max_pages, len(reader.pages))
            return "\n".join(reader.pages[i].extract_text() or "" for i in range(pages))
        except Exception:
            return ""

def parse_strict_dates(text: str) -> list[datetime]:
    dts: list[datetime] = []

    for y, m, d, hh, mm, ss in RX_ISO.findall(text):
        dts.append(datetime(int(y), int(m), int(d), int(hh), int(mm), int(ss) if ss else 0))

    for y, m, d in RX_YMD.findall(text):
        dts.append(datetime(int(y), int(m), int(d)))

    for d, m, y in RX_DMY.findall(text):
        dts.append(datetime(int(y), int(m), int(d)))

    for d, mes, y, hh, mm, ss in RX_ES.findall(text):
        day = int(d)
        month = MONTHS_ES[mes.lower()]
        hour = int(hh) if hh else 0
        minute = int(mm) if mm else 0
        sec = int(ss) if ss else 0
        dts.append(datetime(int(y), month, day, hour, minute, sec))

    return dts

def pick_invoice_date(text: str) -> datetime | None:
    dts = parse_strict_dates(text)
    if not dts:
        return None
    return max(dts)

_illegal = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

def safe_filename(name: str) -> str:
    return _illegal.sub("_", name).strip()

RX_PREFIX = re.compile(r"^\d{4}[-_\.]\d{2}[-_\.]\d{2}\s*-\s*", re.ASCII)

def strip_existing_date_prefix(stem: str) -> str:
    return RX_PREFIX.sub("", stem)

def build_new_name(original: Path, dt: datetime) -> str:
    prefix = dt.strftime("%Y-%m-%d")
    clean_stem = strip_existing_date_prefix(original.stem)
    return f"{prefix} - {safe_filename(clean_stem)}{original.suffix.lower()}"

def main():
    pdfs = list(FACTURAS_DIR.glob("*.pdf"))
    if not pdfs:
        print("⚠️ No se encontraron PDFs en la carpeta.")
        return

    print(f"📂 Carpeta: {FACTURAS_DIR}")
    for pdf in pdfs:
        text = extract_text_pdf(pdf)
        dt = pick_invoice_date(text) if text else None
        if not dt:
            print(f"❓ {pdf.name} -> No se detectó fecha")
            continue

        new_name = build_new_name(pdf, dt)
        target = pdf.with_name(new_name)

        i = 1
        while target.exists():
            target = target.with_stem(target.stem + f" ({i})")
            i += 1

        pdf.rename(target)
        print(f"✅ {pdf.name} -> {target.name}")

if __name__ == "__main__":
    main()
