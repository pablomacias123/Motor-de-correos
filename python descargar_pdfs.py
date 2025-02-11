import imaplib
import email
from email.header import decode_header
import os
import time
import sys
import win32api
import win32print

# Configuración del correo
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = "luispablosamano01@gmail.com"
EMAIL_PASS = "moci gaoa jkit pyhp"

# Carpeta donde se guardarán los PDFs
DOWNLOAD_FOLDER = "FACTURAS DESCARGADAS"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


try:
    # Conectar al servidor IMAP
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    print("✅ Inicio de sesión exitoso.")

    # Seleccionar la bandeja de entrada
    mail.select("inbox")

    # Buscar correos no leídos
    status, messages = mail.search(None, 'UNSEEN')

    if status != "OK" or not messages[0]:
        print("❌ No hay correos no leídos.")
    else:
        # Lista de IDs de correos
        message_numbers = messages[0].split()
        print(f"📩 Correos no leídos encontrados: {len(message_numbers)}")

        # Procesar cada correo
        for num in message_numbers:
            status, msg_data = mail.fetch(num, "(RFC822)")

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decodificar el asunto
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes) and encoding:
                        subject = subject.decode(encoding, errors="ignore")

                    print(f"\n📨 Procesando correo: {subject}")
                    print(f"✉️  De: {msg.get('From')}")

                    # Variable para almacenar la ruta del PDF descargado
                    pdf_path = None

                    # Recorrer partes del correo en busca de adjuntos
                    for part in msg.walk():
                        if part.get_content_disposition() == "attachment":
                            filename = part.get_filename()
                            if filename:
                                filename, encoding = decode_header(filename)[0]
                                if isinstance(filename, bytes) and encoding:
                                    filename = filename.decode(encoding, errors="ignore")

                                # Verificar que sea un PDF
                                if filename.lower().endswith(".pdf"):
                                    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

                                    try:
                                        # Guardar el archivo
                                        with open(filepath, "wb") as f:
                                            f.write(part.get_payload(decode=True))
                                        print(f"✅ PDF descargado: {filepath}")


                                    except Exception as e:
                                        print(f"❌ Error al guardar {filename}: {e}")

                                else:
                                    print(f"❌ {filename} no es un PDF. No se descargará.")

    print("\n🔚 Proceso finalizado.")

except imaplib.IMAP4.error as e:
    print(f"❌ Error en la conexión IMAP: {e}")
except Exception as e:
    print(f"❌ Ocurrió un error inesperado: {e}")
finally:
    try:
        mail.logout()
    except:
        print("⚠ No se pudo cerrar la sesión correctamente.")

        