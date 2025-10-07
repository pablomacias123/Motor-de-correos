import subprocess
import time
from pathlib import Path
import sys

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent
SCRIPTS = [
    "Descargas.py",
    "limpiar_facturas.py",  
    "Ordenador.py",
    "invertir_paginas.py",
    "unir_facturas.py"      
]

# === FUNCIÓN PARA EJECUTAR CADA SCRIPT ===
def run_script(script_name):
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        print(f"⚠️  No se encontró el script: {script_name}")
        return False

    print(f"\n🚀 Ejecutando: {script_name}\n{'='*60}")
    start = time.time()

    try:
        # ⬇️ Aquí dejamos que los prints se vean en tiempo real
        subprocess.run([sys.executable, str(script_path)], check=True)
        print(f"✅ {script_name} completado en {round(time.time() - start, 2)}s")
        print("-"*60)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {script_name}")
        print(f"📜 Código de salida: {e.returncode}")
        print("-"*60)
        return False

    except Exception as e:
        print(f"⚠️  Error inesperado al ejecutar {script_name}: {e}")
        print("-"*60)
        return False


# === FLUJO PRINCIPAL ===
print("\n=== 🧩 INICIO DEL PROCESO COMPLETO ===\n")

for script in SCRIPTS:
    ok = run_script(script)
    if not ok:
        print(f"\n🛑 Se detiene el flujo por error en {script}. Revisa la carpeta 'errors' o la consola arriba.")
        break
else:
    print("\n🎉 TODOS LOS PROCESOS FINALIZADOS CORRECTAMENTE 🎉")

print("\n=== 🏁 FIN DEL PROCESO ===\n")
