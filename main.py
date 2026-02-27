import subprocess
import time
from pathlib import Path
import sys
import shutil
import os

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent

# Carpetas que deben limpiarse ANTES de ejecutar el proceso
CARPETAS_A_LIMPIAR = [
    BASE_DIR / "FACTURAS DESCARGADAS",
    BASE_DIR / "FACTURAS INVERTIDAS"
]

# Scripts que se ejecutan en orden
SCRIPTS = [
    "Descargas.py",
    "Descargas.py",
    "limpiar_facturas.py",
    "Ordenador.py",
    "invertir_paginas.py",
    "unir_facturas.py"
]

# === LIMPIEZA DE CONTENIDO DE CARPETAS ===
def limpiar_contenido_carpeta(ruta: Path):
    """Elimina SOLO contenido dentro de la carpeta, no la carpeta en sí."""
    if not ruta.exists():
        ruta.mkdir(parents=True, exist_ok=True)
        return

    for item in ruta.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as e:
            print(f" No pude eliminar {item}: {e}")

def limpiar_carpetas_iniciales():
    print(" Limpiando contenido de carpetas de trabajo...\n")
    for carpeta in CARPETAS_A_LIMPIAR:
        limpiar_contenido_carpeta(carpeta)
    print(" Carpetas listas.\n")


# === FUNCIÓN PARA EJECUTAR CADA SCRIPT ===
def run_script(script_name):
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        print(f"  No se encontró el script: {script_name}")
        return False

    print(f"\n Ejecutando: {script_name}\n{'='*60}")
    start = time.time()

    try:
        # Ejecutar script con salida en tiempo real
        subprocess.run([sys.executable, str(script_path)], check=True)
        print(f" {script_name} completado en {round(time.time() - start, 2)}s")
        print("-" * 60)
        return True

    except subprocess.CalledProcessError as e:
        print(f" Error en {script_name}")
        print(f" Código de salida: {e.returncode}")
        print("-" * 60)
        return False

    except Exception as e:
        print(f"  Error inesperado al ejecutar {script_name}: {e}")
        print("-" * 60)
        return False


# === FLUJO PRINCIPAL ===

print("\n=== 🧩 INICIO DEL PROCESO COMPLETO ===\n")

# 🔥 LIMPIAR CARPETAS ANTES DE TODO 🔥
limpiar_carpetas_iniciales()

# Ejecutar scripts en orden
for script in SCRIPTS:
    ok = run_script(script)
    if not ok:
        print(f"\n Se detiene el flujo por error en {script}. Revisa la carpeta 'errors' o la consola arriba.")
        break
else:
    print("\n TODOS LOS PROCESOS FINALIZADOS CORRECTAMENTE 🎉")

print("\n===  FIN DEL PROCESO ===\n")
