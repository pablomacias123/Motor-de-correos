import imaplib
import email
from email.header import decode_header
import os
import sys
import hashlib
from datetime import datetime
import socket
import time, re, gc
from imaplib import IMAP4
from hash_manager import load_existing_hashes, append_hash, calculate_hash


# ==========================
# Tiempos y robustez
# ==========================
socket.setdefaulttimeout(120)  # timeout alto para Yahoo/IMAP

BATCH_SIZE = 100           # procesa en lotes de 100 correos
KEEPALIVE_EVERY = 25       # cada 25 hace NOOP (mantener viva la sesión)
RECONNECT_EVERY = 400      # reconecta cada 400 correos
RETRY_FETCHES = 3          # reintentos para FETCH del cuerpo
RETRY_BACKOFF = 1.0        # backoff incremental (segundos)

sys.stdout.reconfigure(encoding='utf-8')

# ==========================
# CONFIG (Yahoo)
# ==========================
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER  = "pablo.macias234@gmail.com"
IMPAP_PORT   = 993
EMAIL_PASS  = "dzkqwefrclfrfgef"   

BASE_DIR = os.getcwd()
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "FACTURAS DESCARGADAS")  
META_FOLDER     = os.path.join(BASE_DIR, "FACTURAS_META")         
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(META_FOLDER, exist_ok=True)

HASHES_DB = os.path.join(META_FOLDER, "_hashes.db")
LOG_CSV   = os.path.join(META_FOLDER, "duplicates_log.csv")
NO_SAVE_CSV = os.path.join(META_FOLDER, "seen_no_save.csv")  # log de “vistos sin descarga”

DUPLICATE_FOLDER = "DUPLICADOS"
REVIEW_FOLDER    = "REVISA_MANUAL"   # opcional para rescate

ALWAYS_MOVE_IF_DUPLICATES = False    # True = mueve también correos mixtos (nuevos+duplicados)

# Solo NO LEÍDOS en INBOX
ONLY_UNSEEN = True
MODO_PRUEBA = True 
MAILBOX_NAME = "PRUEBAS_BOT" if MODO_PRUEBA else "INBOX"


# Verbosidad
VERBOSE = True
USE_BODYSTRUCTURE_FILTER = False

# Marcas de rescate
FLAG_IF_NO_SAVE = True               #  si no se guardó ningún PDF
MOVE_IF_NO_SAVE = False              # mover a REVISA_MANUAL si no se guardó (déjalo False si solo quieres la estrella)

# ==========================
# UTILIDADES
# ==========================
def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)

def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256(); h.update(data); return h.hexdigest()

def load_existing_hashes() -> set:
    """
    Carga todos los hashes conocidos desde HASHES_DB.
    Ya no re-hashea PDFs viejos para evitar que el arranque se vuelva lento.
    """
    hashes = set()

    if os.path.exists(HASHES_DB):
        try:
            with open(HASHES_DB, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        hashes.add(line)
        except Exception as e:
            vprint(f"⚠️  No pude leer _hashes.db: {e}")

    return hashes


def append_hash(h: str):
    try:
        with open(HASHES_DB, "a", encoding="utf-8") as f:
            f.write(h + "\n")
    except Exception as e:
        vprint(f"⚠️  No pude escribir _hashes.db: {e}")

def log_duplicate_row(row: list):
    header_needed = not os.path.exists(LOG_CSV)
    try:
        with open(LOG_CSV, "a", encoding="utf-8") as f:
            if header_needed:
                f.write("timestamp,subject,from,date,message_id,attachment,hash\n")
            f.write(",".join(['"'+c.replace('"','""')+'"' for c in row]) + "\n")
    except Exception as e:
        vprint(f"  No pude escribir duplicates_log.csv: {e}")

def log_seen_no_save(row: list):
    header_needed = not os.path.exists(NO_SAVE_CSV)
    try:
        with open(NO_SAVE_CSV, "a", encoding="utf-8") as f:
            if header_needed:
                f.write("timestamp,reason,subject,from,date,message_id\n")
            f.write(",".join(['"'+c.replace('"','""')+'"' for c in row]) + "\n")
    except Exception as e:
        vprint(f"⚠️  No pude escribir seen_no_save.csv: {e}")

def decode_maybe(value):
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for val, enc in parts:
        if isinstance(val, bytes):
            try:
                out.append(val.decode(enc or "utf-8", errors="ignore"))
            except Exception:
                out.append(val.decode("latin-1", errors="ignore"))
        else:
            out.append(val)
    return "".join(out)

def unique_path(base_folder: str, filename: str) -> str:
    name, ext = os.path.splitext(filename)
    candidate = os.path.join(base_folder, filename)
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(base_folder, f"{name} ({i}){ext}")
        i += 1
    return candidate

def ensure_label_and_reselect_inbox(mail, folder_name: str):
    try:
        ok, _ = mail.select(folder_name)
        if ok == "OK":
            mail.select(MAILBOX_NAME)
            return
    except Exception:
        pass
    try:
        res, msg = mail.create(folder_name)
        if res != "OK" and not (msg and msg[0] and b"exist" in msg[0].lower()):
            print(f" CREATE {folder_name} -> {res}: {msg}")
    except Exception as e:
        print(f" CREATE lanzó excepción (puede que ya exista): {e}")
    mail.select("INBOX")

def move_message_from_inbox(mail, num, dest_label: str, delete_from_inbox=True):
    ensure_label_and_reselect_inbox(mail, dest_label)
    try:
        res, _ = mail.copy(num, dest_label)
        if res == "OK":
            if delete_from_inbox:
                mail.store(num, '+FLAGS', r'(\Deleted)')
                mail.expunge()
            return True
        else:
            vprint(f" COPY devolvió: {res}")
            return False
    except Exception as e:
        vprint(f" No se pudo mover {num} -> {dest_label}: {e}")
        return False

def flag_message(mail, num):
    try:
        mail.store(num, '+FLAGS', r'(\Flagged)')
        return True
    except Exception as e:
        vprint(f" No se pudo poner bandera a {num}: {e}")
        return False

def mark_seen_strict(mail, num, retries=3, delay=0.25):
    # 1) Marca como leído (preferir .SILENT para evitar ecos)
    res, _ = mail.store(num, '+FLAGS.SILENT', r'(\Seen)')
    if res != "OK":
        print(f"   ⚠️ store -> {res}; intentando sin .SILENT…")
        res, _ = mail.store(num, '+FLAGS', r'(\Seen)')

    def has_seen(resp):
        """Busca \\Seen en todos los tuples del FETCH."""
        if not resp:
            return False
        for part in resp:
            if isinstance(part, tuple):
                line = part[0].decode(errors='ignore') if isinstance(part[0], (bytes, bytearray)) else ''
                if '\\Seen' in line:
                    return True
        return False

    # Reintentos con FETCH FLAGS
    for _i in range(retries):
        ok, data = mail.fetch(num, '(FLAGS)')
        if ok == 'OK' and has_seen(data):
            print("   👁️  Marcado como leído (verificado).")
            return True
        time.sleep(delay)

    # Fallback: verificar por UID
    ok, ud = mail.fetch(num, '(UID)')
    uid = None
    if ok == 'OK' and ud and isinstance(ud[0], tuple):
        m = re.search(r'UID (\d+)', ud[0][0].decode(errors='ignore'))
        if m:
            uid = m.group(1)

    if uid:
        for _i in range(retries):
            ok, data = mail.uid('fetch', uid, '(FLAGS)')
            if ok == 'OK' and has_seen(data):
                print("     Marcado como leído (verificado por UID).")
                return True
            time.sleep(delay)

    print("     No se pudo verificar el marcado como leído (posible retardo del servidor).")
    return False

# ===== Keepalive / reconexión =====
def safe_noop(mail):
    try:
        mail.noop()
        return True
    except Exception as e:
        print(f"     NOOP falló: {e}")
        return False

def reconnect_and_select():
    print(" Reconexion IMAP…")
    m = imaplib.IMAP4_SSL(IMAP_SERVER)
    m.login(EMAIL_USER, EMAIL_PASS)
    ok, _ = m.select(MAILBOX_NAME)
    print(f"   → SELECT MAILBOX_NAME -> {ok}")
    return m

def ensure_connected(mail):
    """Si NOOP falla, reconecta y vuelve a INBOX."""
    if not safe_noop(mail):
        try:
            mail.logout()
        except Exception:
            pass
        return reconnect_and_select()
    return mail

def fetch_body_robust(mail, num, max_retries=RETRY_FETCHES):
    """Intenta BODY.PEEK[] con reintentos; si falla, hace fallback por UID."""
    for i in range(max_retries):
        try:
            status, data = mail.fetch(num, "(BODY.PEEK[])")
            if status == "OK" and data and any(isinstance(x, tuple) for x in data):
                return "OK", data
            print(f"     FETCH intento {i+1}/{max_retries} -> {status}")
        except (IMAP4.abort, IMAP4.error, socket.timeout, OSError) as e:
            print(f"     FETCH excepción intento {i+1}/{max_retries}: {e}")
        time.sleep(RETRY_BACKOFF * (i+1))

    # Fallback por UID
    try:
        s, ud = mail.fetch(num, "(UID)")
        uid = None
        if s == "OK" and ud and isinstance(ud[0], tuple):
            m = re.search(r"UID (\d+)", ud[0][0].decode(errors="ignore"))
            if m: uid = m.group(1)
        if uid:
            for i in range(2):
                try:
                    s2, d2 = mail.uid("fetch", uid, "(BODY.PEEK[])")
                    print(f"   ↪ UID FETCH intento {i+1} -> {s2}")
                    if s2 == "OK" and d2 and any(isinstance(x, tuple) for x in d2):
                        return s2, d2
                except (IMAP4.abort, IMAP4.error, socket.timeout, OSError) as e:
                    print(f"   ⚠️  UID FETCH excepción: {e}")
                time.sleep(RETRY_BACKOFF * (i+1))
    except Exception as e:
        print(f"   ⚠️  UID lookup excepción: {e}")

    return "NO", []

# ==========================
# BÚSQUEDA (robusta para Yahoo)
# ==========================
def robust_search_unseen(mail):
    attempts = [
        ("SEARCH UNSEEN",        lambda: mail.search(None, 'UNSEEN')),
        ("SEARCH (UNSEEN)",      lambda: mail.search(None, '(UNSEEN)')),
        ("UID SEARCH UNSEEN",    lambda: mail.uid('search', None, 'UNSEEN')),
        ("UID SEARCH (UNSEEN)",  lambda: mail.uid('search', None, '(UNSEEN)')),
    ]
    for label, fn in attempts:
        try:
            status, data = fn()
            print(f"   ↪ {label} -> {status}")
            if status == "OK":
                return status, data
        except Exception as e:
            print(f"   ↪ {label} error: {e}")

    # Plan C: SEARCH ALL y filtrar por FLAGS
    try:
        status, data = mail.search(None, 'ALL')
        print(f"   ↪ SEARCH ALL -> {status}")
        if status != "OK" or not data or not data[0]:
            return status, data
        all_ids = data[0].split()
        unseen_ids = []
        BATCH = 500
        for i in range(0, len(all_ids), BATCH):
            batch_ids = b','.join(all_ids[i:i+BATCH])
            s2, resp = mail.fetch(batch_ids, '(FLAGS)')
            print(f"      · FETCH FLAGS {i+1}-{min(i+BATCH, len(all_ids))} -> {s2}")
            if s2 != "OK":
                continue
            for part in resp:
                if isinstance(part, tuple) and part[0]:
                    line = part[0].decode(errors='ignore')
                    try:
                        mid = line.split()[0]
                        if "\\Seen" not in line:
                            unseen_ids.append(mid.encode())
                    except Exception:
                        pass
        if unseen_ids:
            return "OK", [b' '.join(unseen_ids)]
        else:
            return "OK", [b'']
    except Exception as e:
        print(f"   ↪ SEARCH ALL error: {e}")
        return "NO", [b'']

# ==========================
# PROGRAMA
# ==========================
def main():
    existing_hashes = load_existing_hashes()
    print(f" Hashes precargados: {len(existing_hashes)}")

    try:
        print(" Conectando a IMAP…")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        print(" Login IMAP OK.")

        code, _ = mail.select(MAILBOX_NAME)
        print(f" SELECT MAILBOX_NAME -> {code}")

        # Garantiza carpetas auxiliares
        ensure_label_and_reselect_inbox(mail, DUPLICATE_FOLDER)
        ensure_label_and_reselect_inbox(mail, REVIEW_FOLDER)
        print(f"  Carpetas garantizadas: {DUPLICATE_FOLDER}, {REVIEW_FOLDER}")

        # Buscar NO LEÍDOS robusto
        print(" Buscando NO LEÍDOS en INBOX (Yahoo)…")
        status, messages = robust_search_unseen(mail)
        print(f" SEARCH (robusto) -> {status}")

        if status != "OK" or not messages or not messages[0]:
            print(" No hay correos NO LEÍDOS en INBOX.")
            return

        message_numbers = messages[0].split()
        print(f" Mensajes a procesar (INBOX, UNREAD): {len(message_numbers)}")

        processed = 0
        mail = ensure_connected(mail)  # por si algo quedó colgado

        for start in range(0, len(message_numbers), BATCH_SIZE):
            batch = message_numbers[start:start+BATCH_SIZE]
            print(f"\n Lote {start+1}-{start+len(batch)} de {len(message_numbers)}")

            for num in batch:
                try:
                    # Keepalive periódico
                    if (processed % KEEPALIVE_EVERY) == 0:
                        mail = ensure_connected(mail)

                    print("\n════════════════════════════════════════")
                    print(f"  Leyendo mensaje ID {num.decode()}")

                    # Cabeceras
                    status, head_data = mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])')
                    print(f"   FETCH HEADERS -> {status}")
                    subject = from_ = date_ = msgid = ""
                    for rp in head_data:
                        if isinstance(rp, tuple):
                            hdr = email.message_from_bytes(rp[1])
                            subject = decode_maybe(hdr.get("Subject"))
                            from_   = decode_maybe(hdr.get("From"))
                            date_   = decode_maybe(hdr.get("Date"))
                            msgid   = decode_maybe(hdr.get("Message-ID")) or ""
                    print(f" Asunto: {subject}")
                    print(f"  De: {from_}")
                    print(f"  Fecha: {date_}")
                    print(f" Message-ID: {msgid}")

                    # (Opcional) BODYSTRUCTURE
                    if USE_BODYSTRUCTURE_FILTER:
                        print(f"  BODYSTRUCTURE de ID {num.decode()}…")
                        status, bs_data = mail.fetch(num, '(BODYSTRUCTURE)')
                        print(f"   FETCH BODYSTRUCTURE -> {status}")
                        bs_bytes = b""
                        for rp in bs_data:
                            if isinstance(rp, tuple):
                                for part in rp:
                                    if isinstance(part, (bytes, bytearray)):
                                        bs_bytes += part
                            elif isinstance(rp, (bytes, bytearray)):
                                bs_bytes += rp
                        bs_lower = bs_bytes.lower()
                        has_pdf = (b'application' in bs_lower and b'pdf' in bs_lower)
                        if not has_pdf:
                            print("     BODYSTRUCTURE indica que NO hay PDFs. Se marca leído y se sigue.")
                            mark_seen_strict(mail, num)
                            # (Opcional) log/flag de no-guardado
                            if FLAG_IF_NO_SAVE:
                                flag_message(mail, num)
                            log_seen_no_save([
                                datetime.now().isoformat(timespec="seconds"),
                                "NO_PDF_BODYSTRUCTURE", subject, from_, date_, msgid
                            ])
                            continue

                    # CUERPO robusto
                    status, msg_data = fetch_body_robust(mail, num)
                    print(f"   FETCH BODY (robusto) -> {status}")
                    if status != "OK":
                        print("    FETCH_BODY_FAILED (tras reintentos). Marcar leído y continuar.")
                        mark_seen_strict(mail, num)
                        if FLAG_IF_NO_SAVE:
                            flag_message(mail, num)
                        log_seen_no_save([
                            datetime.now().isoformat(timespec="seconds"),
                            "FETCH_BODY_FAILED", subject, from_, date_, msgid
                        ])
                        processed += 1
                        continue

                    saved_any_pdf = False
                    found_any_duplicate = False
                    found_any_pdf_part = False

                    # Procesar partes
                    for response_part in msg_data:
                        if not isinstance(response_part, tuple):
                            continue
                        msg = email.message_from_bytes(response_part[1])

                        for i, part in enumerate(msg.walk(), start=1):
                            cdisp = part.get("Content-Disposition")
                            ctype = part.get_content_type()
                            filename = part.get_filename()
                            filename_dec = decode_maybe(filename) if filename else ""

                            vprint(f"   ├─ Parte #{i}: ctype={ctype} cdisp={cdisp} fname={filename_dec}")

                            is_pdf = (filename_dec.lower().endswith(".pdf")) or (ctype == "application/pdf")
                            if not is_pdf:
                                vprint("   │  → No es PDF, se omite.")
                                continue
                            found_any_pdf_part = True

                            try:
                                data = part.get_payload(decode=True)
                            except Exception as e:
                                print(f"    Error al decodificar parte #{i}: {e}")
                                continue

                            if not data:
                                print(f"     Parte #{i}: sin datos, se omite.")
                                continue

                            if not filename_dec:
                                filename_dec = f"adjunto_{i}.pdf"

                            h = sha256_bytes(data)
                            if h in existing_hashes:
                                found_any_duplicate = True
                                print("    Duplicado detectado: NO se guarda el adjunto.")
                                print(f"      • Adj: {filename_dec}")
                                print(f"      • Hash: {h}")
                                log_duplicate_row([
                                    datetime.now().isoformat(timespec="seconds"),
                                    subject, from_, date_, msgid, filename_dec, h
                                ])
                                continue

                            out_path = unique_path(DOWNLOAD_FOLDER, filename_dec)
                            try:
                                with open(out_path, "wb") as f:
                                    f.write(data)
                                existing_hashes.add(h)
                                append_hash(h)
                                saved_any_pdf = True
                                print(f"    PDF guardado: {out_path}")
                            except Exception as e:
                                print(f"   ❌ Error al guardar {filename_dec}: {e}")

                    # Marcar SIEMPRE como leído
                    mark_seen_strict(mail, num)

                    # Política de mover/flag
                    if found_any_duplicate and (ALWAYS_MOVE_IF_DUPLICATES or not saved_any_pdf):
                        print("    Hay duplicados (política de mover activa). Moviendo a DUPLICADOS…")
                        mail.select(MAILBOX_NAME)  # asegurar que estamos en MAILBOX_NAME antes de mover
                        moved = move_message_from_inbox(mail, num, DUPLICATE_FOLDER, delete_from_inbox=True)
                        print(f"   → Movimiento: {'OK' if moved else 'FALLÓ'}")
                    elif found_any_duplicate and saved_any_pdf:
                        print("   ⚑ Hubo adjuntos nuevos y duplicados. Colocando bandera (\\Flagged)…")
                        flag_message(mail, num)

                    if not saved_any_pdf and not found_any_duplicate:
                        print("     Mensaje sin PDFs válidos.")

                    processed += 1

                    # Reconexión periódica
                    if (processed % RECONNECT_EVERY) == 0:
                        try:
                            mail.logout()
                        except Exception:
                            pass
                        mail = reconnect_and_select()

                except (IMAP4.abort, IMAP4.error, socket.timeout, OSError) as e:
                    print(f"    Excepción IMAP en mensaje {num.decode()}: {e}")
                    # Reconnect y seguir con el siguiente
                    try:
                        mail.logout()
                    except Exception:
                        pass
                    mail = reconnect_and_select()
                    continue
                except Exception as e:
                    print(f"    Excepción no controlada en mensaje {num.decode()}: {e}")
                    continue

            # Limpieza ligera entre lotes
            gc.collect()
            time.sleep(0.3)

        print("\n🔚 Proceso finalizado.")

    except imaplib.IMAP4.error as e:
        print(f" Error IMAP: {e}")
    except Exception as e:
        print(f" Error inesperado: {e}")
    finally:
        try:
            mail.logout()
        except Exception:
            print(" No se pudo cerrar la sesión correctamente.")

if __name__ == "__main__":
    main()
