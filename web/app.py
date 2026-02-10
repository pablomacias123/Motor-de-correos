import os
import glob
import threading
import subprocess
from datetime import datetime
import os
import signal

from flask import Flask, render_template, jsonify, send_file, request

app = Flask(__name__)

process = None
process_start_time = None

# =========================
# RUTAS IMPORTANTES
# =========================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.abspath(os.path.dirname(__file__))

LOG_DIR = os.path.join(WEB_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "motor.log")

MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

FACTURAS_FINAL = os.path.join(BASE_DIR, "FACTURAS FINAL")
FACTURAS_ERRORS = os.path.join(BASE_DIR, "Errors")
FACTURAS_DESCARGADAS = os.path.join(BASE_DIR, "FACTURAS DESCARGADAS")

# =========================
# ESTADO GLOBAL
# =========================
STATE = {
    "running": False,
    "last_run": None,
    "exit_code": None,
    "last_pdf": None,
    "error": None
}


def ensure_folders():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(FACTURAS_FINAL, exist_ok=True)
    os.makedirs(FACTURAS_ERRORS, exist_ok=True)
    os.makedirs(FACTURAS_DESCARGADAS, exist_ok=True)


def write_log(line: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clear_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")


def find_latest_final_pdf():
    pdfs = glob.glob(os.path.join(FACTURAS_FINAL, "*.pdf"))
    if not pdfs:
        return None
    pdfs.sort(key=os.path.getmtime, reverse=True)
    return pdfs[0]


def run_motor():
    """Corre main.py en un hilo separado y va guardando logs."""
    global process, process_start_time
    

    try:
        STATE["running"] = True
        STATE["exit_code"] = None
        STATE["error"] = None
        STATE["last_pdf"] = None
        STATE["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        process_start_time = STATE["last_run"]

        clear_log()
        write_log("============================================")
        write_log("Motor iniciado")
        write_log(f"Hora: {STATE['last_run']}")
        write_log("============================================")

        # Ejecutar main.py
        cmd = ["python", "-X", "utf8", MAIN_SCRIPT]


        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"

        )

        for line in process.stdout:
            write_log(line.rstrip())

        process.wait()
        STATE["exit_code"] = process.returncode

        latest_pdf = find_latest_final_pdf()
        if latest_pdf:
            STATE["last_pdf"] = os.path.basename(latest_pdf)

        if process.returncode == 0:
            write_log("\n✅ Proceso finalizado correctamente.")
        else:
            write_log(f"\n❌ Proceso terminó con error. Código: {process.returncode}")

    except Exception as e:
        STATE["error"] = str(e)
        write_log(f"\n❌ ERROR INTERNO: {e}")

    finally:
        STATE["running"] = False
        process = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(STATE)

@app.route("/api/run", methods=["POST"])
def api_run():
    if STATE["running"]:
        return jsonify({"ok": False, "message": "Ya hay un proceso corriendo"}), 409

    t = threading.Thread(target=run_motor, daemon=True)
    t.start()

    return jsonify({"ok": True, "message": "Motor iniciado"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global process

    if not STATE["running"] or process is None:
        return jsonify({"ok": False, "message": "No hay proceso en ejecución"}), 409

    try:
        process.terminate()

        try:
            process.wait(timeout=2)
        except:
            process.kill()

        write_log("\n⛔ Proceso detenido manualmente desde el panel.")
        STATE["exit_code"] = -1
        STATE["running"] = False

        return jsonify({"ok": True, "message": "Proceso detenido"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/logs")
def api_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": ""})

    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        return jsonify({"logs": f.read()})
    
@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    try:
        # Primero detener el motor si está corriendo
        global process
        if STATE["running"] and process is not None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except:
                process.kill()

        write_log("\n🛑 Servidor Flask apagado desde el panel...")

        # Apagar Flask
        os.kill(os.getpid(), signal.SIGINT)

        return jsonify({"ok": True, "message": "Servidor apagado"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/download")
def api_download():
    latest_pdf = find_latest_final_pdf()
    if not latest_pdf:
        return jsonify({"ok": False, "message": "No hay PDF final aún"}), 404

    return send_file(latest_pdf, as_attachment=True)


@app.route("/api/open-folder", methods=["POST"])
def api_open_folder():
    data = request.get_json(force=True)
    which = data.get("which")

    mapping = {
        "final": FACTURAS_FINAL,
        "errors": FACTURAS_ERRORS,
        "descargadas": FACTURAS_DESCARGADAS,
    }

    

    folder = mapping.get(which)
    if not folder:
        return jsonify({"ok": False, "message": "Carpeta inválida"}), 400

    # Windows
    try:
        os.startfile(folder)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


if __name__ == "__main__":
    ensure_folders()
    app.run(debug=True)
