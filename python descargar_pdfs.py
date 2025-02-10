import imaplib
import email
from email.header import decode_header
import os

# Datos de conexión
email_user = "consorciobanco@yahoo.com"  # Cambia esto por tu correo de Yahoo
email_pass = "oocbouotgtlqdior"  # Usa una contraseña de aplicación si tienes 2FA activado

# Carpeta donde se guardarán los archivos adjuntos
download_folder = r"C:\Users\Usuario\Desktop\Facturas para imprimir"

# Asegurar que la carpeta de destino exista
os.makedirs(download_folder, exist_ok=True)

# Conectar al servidor IMAP de Yahoo
mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")

try:
    # Iniciar sesión
    mail.login(email_user, email_pass)
    print("✅ Inicio de sesión exitoso.")

    # Seleccionar el buzón de entrada
    mail.select("inbox")

    # Buscar correos no leídos (UNSEEN)
    status, messages = mail.search(None, 'UNSEEN')

    if status != "OK" or not messages[0]:
        print("❌ No se encontraron correos no leídos.")
    else:
        # Obtener la lista de identificadores de los correos y ordenarlos de más antiguo a más reciente
        message_numbers = messages[0].split()
        
        print(f"📩 Correos no leídos encontrados: {len(message_numbers)}")

        # Procesar en orden cronológico (del más antiguo al más reciente)
        for num in message_numbers:
            status, msg_data = mail.fetch(num, "(RFC822)")  # Obtener el correo

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])  # Crear objeto de correo

                    # Decodificar el asunto del correo
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    print(f"\n📨 Procesando correo: {subject}")
                    print(f"✉️  De: {msg.get('From')}")

                    # Si el correo tiene múltiples partes (texto + adjuntos)
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            filename = part.get_filename()

                            # Si hay un archivo adjunto
                            if filename:
                                filename, encoding = decode_header(filename)[0]
                                if isinstance(filename, bytes):
                                    filename = filename.decode(encoding or "utf-8")

                                # Asegurar que sea un archivo PDF
                                if filename.lower().endswith(".pdf"):
                                    filepath = os.path.join(download_folder, filename)

                                    # Guardar el archivo adjunto
                                    with open(filepath, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    print(f"✅ Archivo guardado: {filepath}")
                                else:
                                    print(f"❌ {filename} no es un PDF. No se descargará.")
                            else:
                                print("No se encontró un archivo adjunto válido en este correo.")

    print("\n🔚 Proceso finalizado.")

except imaplib.IMAP4.error as e:
    print(f"❌ Error en la conexión: {e}")

finally:
    # Cerrar la conexión con el servidor
    mail.logout()
