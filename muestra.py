import imaplib
import email
from email.header import decode_header

# Datos de conexión
email_user = "consorciobanco@yahoo.com"  # Cambia esto por tu correo de Yahoo
email_pass = "oocbouotgtlqdior"  # Usa una contraseña de aplicación si tienes 2FA activado


# Conectar al servidor IMAP de Yahoo
mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")

try:
    mail.login(email_user, email_pass)
    print("✅ Inicio de sesión exitoso.")

    # Seleccionar la bandeja de entrada
    mail.select("inbox")

    # Buscar correos no leídos
    status, messages = mail.search(None, 'UNSEEN')

    if status != "OK" or not messages[0]:
        print("❌ No se encontraron correos no leídos.")
    else:
        message_numbers = messages[0].split()
        print(f"📩 Correos no leídos encontrados: {len(message_numbers)}")

        for num in message_numbers:
            status, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decodificar el asunto del correo
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    print(f"\n📨 Correo: {subject}")
                    print(f"✉️  De: {msg.get('From')}")
    
    print("\n🔚 Proceso finalizado.")

except imaplib.IMAP4.error as e:
    print(f"❌ Error en la conexión: {e}")

finally:
    mail.logout()
