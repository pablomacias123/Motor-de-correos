import imaplib


usuario = ""
contrasena = ""  

try:
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(usuario, contrasena)

   
    mail.select("inbox")

    
    status, mensajes = mail.search(None, "ALL")

    
    mensajes = mensajes[0].split()

    
    total_correos = len(mensajes)
    print(f"Total de correos a eliminar: {total_correos}")

    # Si hay correos, proceder con la eliminación
    if total_correos > 5:
        for num in mensajes:
            mail.store(num, '+FLAGS', '\\Deleted')
            print(f"✉️ Correo con ID {num.decode()} marcado para eliminación.")

        
        mail.expunge()
        print("✅ Todos los correos marcados han sido eliminados permanentemente.")
    else:
        print("❌ No hay correos para eliminar.")

    
    mail.close()
    mail.logout()
    print("Sesión cerrada correctamente.")

except Exception as e:
    print(f"Error: {e}")



