import tkinter as tk
from src.ui import BuscadorNormasUI
import sys
import os

def check_pdf_directories_exist():
    """
    Verifica que los directorios 'data/rt' y 'data/niif_nic' existan y no estén vacíos.
    """
    rt_dir = 'data/rt'
    niif_nic_dir = 'data/niif_nic'
    dirs_to_check = [rt_dir, niif_nic_dir]
    
    error_messages = []

    for directory in dirs_to_check:
        if not os.path.isdir(directory):
            error_messages.append(f"El directorio '{directory}' no existe. Por favor, créalo.")
        elif not any(fname.lower().endswith('.pdf') for fname in os.listdir(directory)):
            error_messages.append(f"El directorio '{directory}' no contiene ningún archivo PDF.")

    if error_messages:
        full_error_message = "\n".join(error_messages)
        print(f"ERROR: {full_error_message}")
        try:
            root = tk.Tk()
            root.withdraw()
            tk.messagebox.showerror("Error de Configuración", full_error_message)
            root.destroy()
        except tk.TclError:
            # Si hay problemas con Tkinter, la salida por consola es suficiente.
            pass
        sys.exit(1)

def main():
    """
    Función principal que inicializa la aplicación del Buscador de Normas Contables.
    """
    print("[INFO] Iniciando aplicación...")
    check_pdf_directories_exist()
    
    root = tk.Tk()
    root.title("Buscador de Normas Contables")
    root.geometry("1200x700")
    
    app = BuscadorNormasUI(root)
    print("[INFO] Interfaz gráfica iniciada.")
    root.mainloop()

if __name__ == "__main__":
    main()
