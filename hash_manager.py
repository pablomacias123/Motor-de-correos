from pathlib import Path
import hashlib

BASE_DIR = Path(__file__).resolve().parent
HASHES_DB = BASE_DIR / "_hashes.db"


# === CARGAR HASHES EXISTENTES ===
def load_existing_hashes():
    """Carga los hashes ya registrados sin re-hashear PDFs viejos."""
    if not HASHES_DB.exists():
        return set()

    hashes = set()
    try:
        with open(HASHES_DB, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    hashes.add(line)
    except Exception as e:
        print(f" No se pudo leer _hashes.db: {e}")

    return hashes


# === AGREGAR NUEVO HASH ===
def append_hash(h: str):
    """Guarda un hash nuevo en _hashes.db."""
    try:
        with open(HASHES_DB, "a", encoding="utf-8") as f:
            f.write(h + "\n")
    except Exception as e:
        print(f" No se pudo escribir _hashes.db: {e}")


# === CALCULAR HASH SHA256 DE UN ARCHIVO ===
def calculate_hash(pdf_path: Path) -> str:
    """Calcula el hash SHA256 de un archivo PDF."""
    sha256 = hashlib.sha256()
    try:
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
    except Exception as e:
        print(f" No se pudo calcular hash de {pdf_path.name}: {e}")
        return ""
    return sha256.hexdigest()
