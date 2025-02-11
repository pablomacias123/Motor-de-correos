import win32print
import win32api
import os

# Ruta del archivo PDF
pdf_path = os.path.abspath("C:\\Users\\luisp\\OneDrive\\Escritorio\\Trabajos de la uni\\240100-SAAL.pdf")

# Nombre de la impresora
printer_name = "Brother DCP-T720DW Printer"

# Configurar la impresora
printer = win32print.OpenPrinter(printer_name)
printer_info = win32print.GetPrinter(printer, 2)

# Enviar a imprimir
try:
    win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer_name}"', ".", 0)
    print(f"✅ Archivo enviado a la impresora: {printer_name}")
except Exception as e:
    print(f"❌ Error al imprimir: {e}")
