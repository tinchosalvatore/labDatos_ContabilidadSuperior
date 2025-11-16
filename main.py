import tkinter as tk
from src.ui import BuscadorNormasUI
import sys
import os

def check_pdfs_exist():
    """
    Verifica que los archivos PDF necesarios (NCA.pdf y NIFF.pdf) existan en la carpeta 'data/'.
    Si alguno no se encuentra, muestra un mensaje de error y sale de la aplicación.
    """
    nca_path = 'data/NCA.pdf'
    niff_path = 'data/NIFF.pdf'

    if not os.path.exists(nca_path):
        print(f"ERROR: Falta el archivo data/NCA.pdf. Por favor, colócalo en la carpeta 'data/'.")
        # Usar messagebox si tkinter ya está inicializado, de lo contrario, solo print y exit.
        try:
            root = tk.Tk()
            root.withdraw() # Ocultar la ventana principal
            tk.messagebox.showerror("Error de Archivo", f"Falta el archivo {nca_path}. Por favor, colócalo en la carpeta 'data/'.")
            root.destroy()
        except:
            pass
        sys.exit(1)
    if not os.path.exists(niff_path):
        print(f"ERROR: Falta el archivo data/NIFF.pdf. Por favor, colócalo en la carpeta 'data/'.")
        try:
            root = tk.Tk()
            root.withdraw()
            tk.messagebox.showerror("Error de Archivo", f"Falta el archivo {niff_path}. Por favor, colócalo en la carpeta 'data/'.")
            root.destroy()
        except:
            pass
        sys.exit(1)

def main():
    """
    Función principal que inicializa la aplicación del Buscador de Normas Contables.
    """
    print("[INFO] Iniciando aplicación...")
    check_pdfs_exist()
    
    root = tk.Tk()
    root.title("Buscador de Normas Contables")
    root.geometry("1200x700")
    
    app = BuscadorNormasUI(root)
    print("[INFO] Interfaz gráfica iniciada.")
    root.mainloop()

if __name__ == "__main__":
    main()
