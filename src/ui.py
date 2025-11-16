import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import os
from typing import List, Dict, Callable

from src.search_engine import SearchEngine

class BuscadorNormasUI:
    """
    Interfaz gráfica con Tkinter para el Buscador de Normas Contables.
    """
    def __init__(self, root: tk.Tk):
        """
        Inicializa la interfaz de usuario.
        
        Args:
            root (tk.Tk): La ventana principal de Tkinter.
        """
        self.root = root
        self.search_engine = SearchEngine()
        self.setup_ui()
        
    def setup_ui(self):
        """
        Configura todos los widgets de la interfaz de usuario.
        """
        self.root.title("🔍 Buscador de Normas Contables NCA/NIFF")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f5f5f5')

        # Configuración de estilos
        style = ttk.Style()
        style.theme_use('clam') # O 'alt', 'default', 'classic'
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'), background='#4CAF50', foreground='white')
        style.map('TButton', background=[('active', '#45a049')])
        style.configure('TCombobox', font=('Arial', 10))
        style.configure('TEntry', font=('Arial', 10))

        # --- Frame Principal (Contenedor de todo) ---
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Sección Superior (Búsqueda) ---
        search_frame = ttk.Frame(main_frame, padding="10")
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Temas principales:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.topic_var = tk.StringVar()
        self.topic_combobox = ttk.Combobox(search_frame, textvariable=self.topic_var,
                                           values=self.search_engine.load_predefined_topics(),
                                           state="readonly", width=40)
        self.topic_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.topic_combobox.set("Selecciona un tema o ingresa uno nuevo")
        self.topic_combobox.bind("<<ComboboxSelected>>", lambda event: self.on_search())

        ttk.Label(search_frame, text="O ingresa tu tema:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.search_entry = ttk.Entry(search_frame, width=40, font=('Arial', 10))
        self.search_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.search_entry.bind("<Return>", lambda event: self.on_search()) # Permite buscar con Enter

        search_button = ttk.Button(search_frame, text="BUSCAR", command=self.on_search)
        search_button.grid(row=1, column=2, padx=10, pady=5, sticky=tk.E)

        history_button = ttk.Button(search_frame, text="HISTORIAL", command=self.show_history)
        history_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.E)
        
        search_frame.grid_columnconfigure(1, weight=1) # Permite que el combobox y entry se expandan

        # --- Sección de Resultados (NCA | NIFF) ---
        results_frame = ttk.Frame(main_frame, padding="10", style='TFrame')
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_columnconfigure(1, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        # Columna NCA
        nca_frame = ttk.LabelFrame(results_frame, text="NCA", padding="10", style='TFrame')
        nca_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        nca_frame.grid_rowconfigure(0, weight=1)
        nca_frame.grid_columnconfigure(0, weight=1)
        self.nca_text = scrolledtext.ScrolledText(nca_frame, wrap=tk.WORD, width=60, height=20,
                                                  font=('Arial', 9), bg='white', fg='black',
                                                  padx=5, pady=5)
        self.nca_text.pack(fill=tk.BOTH, expand=True)
        self.nca_text.tag_config('page', foreground='blue', font=('Arial', 9, 'bold'))
        self.nca_text.tag_config('context', foreground='#666666', font=('Arial', 9, 'italic'))
        self.nca_text.tag_config('matches', foreground='green', font=('Arial', 9, 'bold'))
        self.nca_text.tag_config('button', foreground='blue', underline=True) # Para simular botón

        # Columna NIFF
        niff_frame = ttk.LabelFrame(results_frame, text="NIFF", padding="10", style='TFrame')
        niff_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)
        niff_frame.grid_rowconfigure(0, weight=1)
        niff_frame.grid_columnconfigure(0, weight=1)
        self.niff_text = scrolledtext.ScrolledText(niff_frame, wrap=tk.WORD, width=60, height=20,
                                                   font=('Arial', 9), bg='white', fg='black',
                                                   padx=5, pady=5)
        self.niff_text.pack(fill=tk.BOTH, expand=True)
        self.niff_text.tag_config('page', foreground='blue', font=('Arial', 9, 'bold'))
        self.niff_text.tag_config('context', foreground='#666666', font=('Arial', 9, 'italic'))
        self.niff_text.tag_config('matches', foreground='green', font=('Arial', 9, 'bold'))
        self.niff_text.tag_config('button', foreground='blue', underline=True) # Para simular botón

        # --- Sección Inferior (Material Extra) ---
        extra_material_frame = ttk.Frame(main_frame, padding="10", style='TFrame')
        extra_material_frame.pack(fill=tk.X, pady=5)

        ttk.Label(extra_material_frame, text="📚 Material extra:").pack(side=tk.LEFT, padx=5)
        self.extra_material_label = ttk.Label(extra_material_frame, text="❌ No disponible", font=('Arial', 10, 'bold'))
        self.extra_material_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def on_search(self):
        """
        Maneja el evento de búsqueda cuando se presiona el botón BUSCAR o se selecciona un tema.
        """
        selected_topic = self.topic_var.get()
        entered_term = self.search_entry.get().strip()

        search_term = ""
        if selected_topic and selected_topic != "Selecciona un tema o ingresa uno nuevo":
            search_term = selected_topic
        if entered_term:
            search_term = entered_term
        
        if not search_term:
            messagebox.showwarning("Advertencia", "Ingresa un término de búsqueda o selecciona un tema.")
            return

        # Limpiar campos de entrada
        self.topic_combobox.set("Selecciona un tema o ingresa uno nuevo")
        self.search_entry.delete(0, tk.END)

        # Limpiar resultados anteriores
        self.nca_text.delete(1.0, tk.END)
        self.niff_text.delete(1.0, tk.END)
        self.extra_material_label.config(text="Buscando...")

        # Realizar la búsqueda
        results = self.search_engine.search(search_term)

        # Mostrar resultados
        self.display_results("NCA", results["nca_results"])
        self.display_results("NIFF", results["niff_results"])
        self._update_extra_material_label(results["material_extra"])

    def display_results(self, column: str, results: List[Dict]):
        """
        Muestra los resultados de búsqueda en la columna especificada (NCA o NIFF).
        
        Args:
            column (str): "NCA" o "NIFF".
            results (List[Dict]): Lista de diccionarios de resultados de búsqueda.
        """
        text_widget = self.nca_text if column == "NCA" else self.niff_text
        text_widget.config(state=tk.NORMAL) # Habilitar edición temporalmente
        text_widget.delete(1.0, tk.END)

        if not results:
            text_widget.insert(tk.END, "No se encontraron resultados.\n", 'context')
            text_widget.config(state=tk.DISABLED)
            return

        for res in results:
            page_num = res['page']
            contexts = res['contexts']
            matches = res['matches']

            text_widget.insert(tk.END, f"Página: {page_num} ", 'page')
            text_widget.insert(tk.END, f"({matches} coincidencias)\n", 'matches')
            
            for context_str in contexts:
                text_widget.insert(tk.END, f"  \"{context_str}\"\n", 'context')
            
            # Botón "Abrir PDF" simulado con un tag clickeable
            button_text = "📄 Abrir PDF\n\n"
            text_widget.insert(tk.END, button_text, 'button')
            # Asociar el clic a la función open_pdf
            text_widget.tag_bind('button', '<Button-1>', 
                                 lambda event, col=column, page=page_num: self.open_pdf(col, page))
            text_widget.tag_bind('button', '<Enter>', lambda event: event.widget.config(cursor="hand2"))
            text_widget.tag_bind('button', '<Leave>', lambda event: event.widget.config(cursor=""))

        text_widget.config(state=tk.DISABLED) # Deshabilitar edición

    def _update_extra_material_label(self, material_data: Dict):
        """
        Actualiza el label de material extra.
        """
        if material_data.get('disponible'):
            recursos = ", ".join(material_data.get('recursos', []))
            self.extra_material_label.config(text=f"✅ Disponible: {recursos}", foreground='green')
        else:
            self.extra_material_label.config(text="❌ No disponible", foreground='red')

    def open_pdf(self, pdf_name_key: str, page: int):
        """
        Abre el PDF en la página específica usando webbrowser.
        
        Args:
            pdf_name_key (str): "NCA" o "NIFF".
            page (int): Número de página (1-indexado) a abrir.
        """
        pdf_filename = f"{pdf_name_key}.pdf"
        pdf_path = os.path.abspath(os.path.join('data', pdf_filename))
        
        if not os.path.exists(pdf_path):
            messagebox.showerror("Error", f"El archivo PDF '{pdf_filename}' no se encontró en la carpeta 'data/'.")
            return

        # URL para abrir PDF en una página específica (funciona con la mayoría de los navegadores)
        url = f'file:///{pdf_path}#page={page}'
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el PDF: {e}\nIntenta abrirlo manualmente desde: {pdf_path}")

    def show_history(self):
        """
        Muestra una ventana emergente con el historial de búsquedas.
        """
        history_window = tk.Toplevel(self.root)
        history_window.title("Historial de Búsquedas")
        history_window.geometry("600x400")
        history_window.transient(self.root) # Hace que la ventana de historial dependa de la principal
        history_window.grab_set() # Bloquea la interacción con la ventana principal

        history_frame = ttk.Frame(history_window, padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(history_frame, text="Últimas búsquedas:", font=('Arial', 12, 'bold')).pack(pady=5)

        history_list_frame = ttk.Frame(history_frame)
        history_list_frame.pack(fill=tk.BOTH, expand=True)

        history_scroll = scrolledtext.ScrolledText(history_list_frame, wrap=tk.WORD, font=('Arial', 10), height=15)
        history_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scroll.config(state=tk.NORMAL)
        history_scroll.delete(1.0, tk.END)

        history_data = self.search_engine.cache.get_history(limit=20) # Mostrar las últimas 20 búsquedas

        if not history_data:
            history_scroll.insert(tk.END, "No hay búsquedas en el historial.\n")
        else:
            for entry in history_data:
                term = entry.get("termino_original", entry.get("termino", "Desconocido"))
                date_str = datetime.fromisoformat(entry["fecha"]).strftime("%Y-%m-%d %H:%M")
                
                display_text = f"[{date_str}] {term}\n"
                history_scroll.insert(tk.END, display_text, 'history_item')
                history_scroll.tag_bind('history_item', '<Button-1>', 
                                        lambda event, t=term: self._select_history_item(t, history_window))
                history_scroll.tag_bind('history_item', '<Enter>', lambda event: event.widget.config(cursor="hand2"))
                history_scroll.tag_bind('history_item', '<Leave>', lambda event: event.widget.config(cursor=""))
                history_scroll.insert(tk.END, "\n") # Espacio entre items

        history_scroll.config(state=tk.DISABLED)

        clear_button = ttk.Button(history_frame, text="Limpiar Historial", command=self._clear_history_and_refresh)
        clear_button.pack(pady=10)

        history_window.protocol("WM_DELETE_WINDOW", lambda: self._on_history_close(history_window))

    def _select_history_item(self, term: str, history_window: tk.Toplevel):
        """
        Selecciona un elemento del historial y realiza la búsqueda.
        """
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, term)
        history_window.destroy() # Cerrar ventana de historial
        self.on_search() # Realizar la búsqueda

    def _clear_history_and_refresh(self):
        """
        Limpia el historial y refresca la ventana de historial.
        """
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres limpiar todo el historial de búsquedas?"):
            self.search_engine.cache.clear_cache()
            # Refrescar la ventana de historial
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.title() == "Historial de Búsquedas":
                    widget.destroy()
            self.show_history() # Reabrir la ventana de historial actualizada

    def _on_history_close(self, history_window: tk.Toplevel):
        """
        Maneja el cierre de la ventana de historial.
        """
        history_window.grab_release()
        history_window.destroy()
