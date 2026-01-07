import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import os
import threading
import queue
from datetime import datetime
from typing import List, Dict, Union

from src.search_engine import SearchEngine

class BuscadorNormasUI:
    """
    Interfaz gráfica con Tkinter para el Buscador de Normas Contables.
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.search_engine = SearchEngine()
        self.search_in_progress = False
        self.search_queue = queue.Queue()
        
        # Cargar todos los temas al inicio
        self.all_topics = self.search_engine.load_predefined_topics()
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._update_topic_list)

        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("🔍 Buscador de Normas Contables (RT vs NIIF-NIC)")
        self.root.geometry("1200x800") # Aumentar altura para la lista
        self.root.configure(bg='#f5f5f5')

        # --- Estilos ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.configure('Search.TButton', background='#4CAF50', foreground='white')
        style.map('Search.TButton', background=[('active', '#45a049'), ('disabled', '#cccccc')])
        style.configure('Clear.TButton', background='#f44336', foreground='white')
        style.map('Clear.TButton', background=[('active', '#d32f2f')])

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Sección de Búsqueda (Refactorizada) ---
        search_frame = ttk.Frame(main_frame, padding=(10, 0))
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Buscar Tema:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Arial', 11))
        self.search_entry.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.search_entry.bind("<Return>", lambda event: self.on_search())

        self.search_button = ttk.Button(search_frame, text="BUSCAR", style='Search.TButton', command=self.on_search)
        self.search_button.grid(row=1, column=2, padx=10, pady=5, sticky=tk.E)

        self.history_button = ttk.Button(search_frame, text="HISTORIAL", style='History.TButton', command=self.show_history)
        self.history_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.E)
        
        search_frame.grid_columnconfigure(1, weight=1)

        # --- Lista de Temas Dinámica ---
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.X, expand=False, padx=10, pady=(0, 5))

        self.topic_listbox = tk.Listbox(list_frame, height=8, font=('Arial', 9), bg='white', borderwidth=1, relief="solid")
        self.topic_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.topic_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.topic_listbox.config(yscrollcommand=scrollbar.set)
        self.topic_listbox.bind('<<ListboxSelect>>', self._on_listbox_select)
        self.topic_listbox.bind('<Double-1>', lambda e: self.on_search())
        
        # Poblar la lista inicialmente con todos los temas
        self._update_topic_list()


        # --- Sección de Resultados ---
        results_frame = ttk.Frame(main_frame, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_columnconfigure(1, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        # Columna RT
        rt_frame = ttk.LabelFrame(results_frame, text="Resolución Técnica (RT)", padding="10")
        rt_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        rt_frame.grid_rowconfigure(0, weight=1)
        rt_frame.grid_columnconfigure(0, weight=1)
        self.rt_text = scrolledtext.ScrolledText(rt_frame, wrap=tk.WORD, font=('Arial', 9), bg='white', state=tk.DISABLED)
        self.rt_text.pack(fill=tk.BOTH, expand=True)
        self.rt_progress = ttk.Progressbar(rt_frame, orient='horizontal', mode='determinate')
        self.rt_progress.pack(fill=tk.X, pady=5, side=tk.BOTTOM)

        # Columna NIIF-NIC
        niif_nic_frame = ttk.LabelFrame(results_frame, text="NIIF-NIC", padding="10")
        niif_nic_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)
        niif_nic_frame.grid_rowconfigure(0, weight=1)
        niif_nic_frame.grid_columnconfigure(0, weight=1)
        self.niif_nic_text = scrolledtext.ScrolledText(niif_nic_frame, wrap=tk.WORD, font=('Arial', 9), bg='white', state=tk.DISABLED)
        self.niif_nic_text.pack(fill=tk.BOTH, expand=True)
        self.niif_nic_progress = ttk.Progressbar(niif_nic_frame, orient='horizontal', mode='determinate')
        self.niif_nic_progress.pack(fill=tk.X, pady=5, side=tk.BOTTOM)
        
        self.setup_text_tags()

        # --- Sección de Material Extra ---
        extra_material_frame = ttk.Frame(main_frame, padding=(10,5))
        extra_material_frame.pack(fill=tk.X, pady=5)
        ttk.Label(extra_material_frame, text="📚 Material extra:").pack(side=tk.LEFT, padx=5)
        self.extra_material_label = ttk.Label(extra_material_frame, text="...", font=('Arial', 10, 'bold'))
        self.extra_material_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _update_topic_list(self, *args):
        """Filtra la lista de temas basándose en el texto de la barra de búsqueda."""
        search_term = self.search_var.get().lower()
        
        # Guardar la selección actual si existe
        current_selection = None
        if self.topic_listbox.curselection():
            current_selection = self.topic_listbox.get(self.topic_listbox.curselection())

        self.topic_listbox.delete(0, tk.END)
        
        if not search_term:
            filtered_topics = self.all_topics # Reverted to show all topics initially
        else:
            filtered_topics = [topic for topic in self.all_topics if search_term in topic.lower()]
            
        for topic in filtered_topics:
            self.topic_listbox.insert(tk.END, topic)

        # Restaurar la selección si todavía está en la lista
        if current_selection in filtered_topics:
            idx = filtered_topics.index(current_selection)
            self.topic_listbox.selection_set(idx)
            self.topic_listbox.activate(idx)
            self.topic_listbox.see(idx)


    def _on_listbox_select(self, event):
        """Cuando se selecciona un tema de la lista, lo pone en la barra de búsqueda."""
        # Evitar errores si la lista está vacía o el evento se dispara incorrectamente
        if not self.topic_listbox.curselection():
            return
            
        selected_index = self.topic_listbox.curselection()[0]
        selected_topic = self.topic_listbox.get(selected_index)
        
        # Desactivar temporalmente el `trace` para evitar un bucle infinito
        # al actualizar programáticamente la variable de búsqueda.
        trace_info = self.search_var.trace_info()
        if trace_info:
            self.search_var.trace_remove("write", trace_info[0][1])
            self.search_var.set(selected_topic)
            self.search_var.trace_add("write", self._update_topic_list)

    def setup_text_tags(self):
        for text_widget in [self.rt_text, self.niif_nic_text]:
            text_widget.tag_config('page', foreground='blue', font=('Arial', 9, 'bold'))
            text_widget.tag_config('context', foreground='#666666', font=('Arial', 9, 'italic'))
            text_widget.tag_config('matches', foreground='green', font=('Arial', 9, 'bold'))
            text_widget.tag_config('button', foreground='blue', underline=True)
            text_widget.tag_bind('button', '<Button-1>', self.on_open_pdf_click)
            text_widget.tag_bind('button', '<Enter>', lambda e: e.widget.config(cursor="hand2"))
            text_widget.tag_bind('button', '<Leave>', lambda e: e.widget.config(cursor=""))

    def on_search(self, event=None):
        if self.search_in_progress:
            return

        term = self.search_var.get().strip()
        if not term:
            messagebox.showwarning("Advertencia", "Ingresa o selecciona un término de búsqueda.")
            return

        self.search_in_progress = True
        self.search_button.config(state=tk.DISABLED)
        self.history_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)

        for widget in [self.rt_text, self.niif_nic_text]:
            widget.config(state=tk.NORMAL)
            widget.delete(1.0, tk.END)
        
        self.rt_progress['value'] = 0
        self.niif_nic_progress['value'] = 0
        self.extra_material_label.config(text="Buscando...")

        self.rt_text.insert(tk.END, f"Buscando '{term}'...\n", 'context')
        self.niif_nic_text.insert(tk.END, f"Buscando '{term}'...\n", 'context')
        for widget in [self.rt_text, self.niif_nic_text]:
            widget.config(state=tk.DISABLED)

        search_thread = threading.Thread(target=self.search_worker, args=(term,))
        search_thread.start()
        self.process_search_queue()

    def search_worker(self, term):
        try:
            # Definir callbacks que ponen datos en la cola
            def rt_prog_cb(progress): self.search_queue.put(('progress', 'RT', progress))
            def rt_res_cb(result): self.search_queue.put(('result', 'RT', result))
            def niif_prog_cb(progress): self.search_queue.put(('progress', 'NIIF-NIC', progress))
            def niif_res_cb(result): self.search_queue.put(('result', 'NIIF-NIC', result))

            self.search_engine.search_progressive(term, rt_prog_cb, rt_res_cb, niif_prog_cb, niif_res_cb)
            
            # Chequear material extra al final
            extra_material = self.search_engine.check_extra_material(term)
            self.search_queue.put(('extra_material', extra_material, None))

        except Exception as e:
            self.search_queue.put(('error', str(e), None))
        finally:
            self.search_queue.put(('done', None, None))

    def process_search_queue(self):
        try:
            while not self.search_queue.empty():
                msg_type, data, value = self.search_queue.get_nowait()

                if msg_type == 'progress':
                    progress_bar = self.rt_progress if data == 'RT' else self.niif_nic_progress
                    progress_bar['value'] = value
                
                elif msg_type == 'result':
                    self.display_single_result(data, value)

                elif msg_type == 'extra_material':
                    self._update_extra_material_label(data)

                elif msg_type == 'error':
                    messagebox.showerror("Error en Búsqueda", f"Ocurrió un error: {data}")

                elif msg_type == 'done':
                    self.search_in_progress = False
                    self.search_button.config(state=tk.NORMAL)
                    self.history_button.config(state=tk.NORMAL)
                    self.search_entry.config(state=tk.NORMAL)
                    self.check_if_results_found()
                    return # Detener el ciclo after

        except queue.Empty:
            pass
        finally:
            if self.search_in_progress:
                self.root.after(100, self.process_search_queue)

    def display_single_result(self, column: str, result: Dict):
        text_widget = self.rt_text if column == 'RT' else self.niif_nic_text
        
        # Limpiar el "Buscando..." la primera vez que llega un resultado
        if "Buscando" in text_widget.get(1.0, "2.0"):
             text_widget.config(state=tk.NORMAL)
             text_widget.delete(1.0, tk.END)

        text_widget.config(state=tk.NORMAL)
        
        page_num = result.get('page')
        pdf_filename = result.get('pdf_filename')
        matches = result.get('matches', 1)

        # ---- Lógica Adaptada ----
        # Unificar 'context' (string, de búsqueda indexada) y 'contexts' (lista, de búsqueda por texto)
        contexts = result.get('contexts')
        if not contexts:
            single_context = result.get('context')
            if single_context:
                contexts = [single_context]
            else:
                contexts = ["No hay más detalles."]

        # Determinar si es un resultado directo del índice
        is_indexed_result = "Fuente:" in contexts[0]

        # --- Presentación del Resultado ---
        if is_indexed_result:
            text_widget.insert(tk.END, f"Fuente Directa en: {pdf_filename}\n", 'page')
        else:
            text_widget.insert(tk.END, f"Página: {page_num} ({pdf_filename}) ", 'page')
            text_widget.insert(tk.END, f"({matches} coincidencias)\n", 'matches')
        
        for context_str in contexts:
            # Para resultados del índice, el contexto es descriptivo y puede tener saltos de línea
            if is_indexed_result:
                formatted_context = context_str.replace('\n', '\n  ')
                text_widget.insert(tk.END, f"  {formatted_context}\n", 'context')
            else:
                text_widget.insert(tk.END, f"  - \"{context_str}\"\n", 'context')
        
        # Botón para abrir el PDF
        if pdf_filename: # Siempre mostrar un botón si hay un PDF asociado
            if page_num == "todo el pdf":
                button_text = f"📄 Abrir PDF completo\n\n"
            elif isinstance(page_num, int):
                button_text = f"📄 Abrir PDF en página {page_num}\n\n"
            else: # Resultados de búsqueda de respaldo no tienen un page_num directo para el botón
                button_text = f"📄 Abrir PDF\n\n" # Botón genérico "Abrir PDF"
            
            button_tag = f"btn_{column}_{pdf_filename}_{page_num}" 
            text_widget.insert(tk.END, button_text, ('button', button_tag))
            text_widget.tag_bind(button_tag, '<Button-1>', 
                                 lambda e, c=column, f=pdf_filename, p=page_num: self.open_pdf(c, f, p))
        else:
             text_widget.insert(tk.END, "\n")

        text_widget.config(state=tk.DISABLED)

    def check_if_results_found(self):
        for widget in [self.rt_text, self.niif_nic_text]:
            if not widget.get(1.0, tk.END).strip() or "Buscando" in widget.get(1.0, "2.0"):
                widget.config(state=tk.NORMAL)
                widget.delete(1.0, tk.END)
                widget.insert(tk.END, "No se encontraron resultados.\n", 'context')
                widget.config(state=tk.DISABLED)

    def _update_extra_material_label(self, material_data: Dict):
        if material_data.get('disponible'):
            recursos = ", ".join(material_data.get('recursos', []))
            self.extra_material_label.config(text=f"✅ Disponible: {recursos}", foreground='green')
        else:
            self.extra_material_label.config(text="❌ No disponible", foreground='red')

    def open_pdf(self, column_key: str, pdf_filename: str, page: Union[int, str, None]):
        """
        Abre el PDF. Si 'page' es "todo el pdf" o None, abre el PDF completo.
        Si 'page' es un número, abre en la página específica.
        """
        folder_map = {
            "RT": "rt",
            "NIIF-NIC": "niif_nic"
        }
        
        target_folder = folder_map.get(column_key)
        # Buscar en las subcarpetas de data/
        if target_folder:
            pdf_path = os.path.abspath(os.path.join('data', target_folder, pdf_filename))
        else: # Si no hay subcarpeta específica, buscar directamente en 'data/'
            pdf_path = os.path.abspath(os.path.join('data', pdf_filename))

        if not os.path.exists(pdf_path):
            messagebox.showerror("Error", f"El archivo PDF '{pdf_filename}' no se encontró en la ruta esperada: '{os.path.dirname(pdf_path)}'.")
            return

        url = f'file:///{pdf_path.replace(" ", "%20")}'
        if isinstance(page, int): # Solo añadir #page=X si es un número de página
            url += f'#page={page}'
        
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el PDF: {e}\nIntenta abrirlo manualmente: {pdf_path}")

    def on_open_pdf_click(self, event):
        # Esta función es un placeholder, el binding se hace directamente en display_single_result
        pass

    def show_history(self):
        """
        Muestra una ventana emergente con el historial de búsquedas, con un layout y estilo mejorados.
        """
        if self.search_in_progress: return

        history_window = tk.Toplevel(self.root)
        history_window.title("Historial de Búsquedas")
        history_window.minsize(500, 300) # Establecer un tamaño mínimo
        history_window.resizable(True, True) # Permitir que la ventana sea redimensionable
        history_window.transient(self.root)
        history_window.grab_set()

        # --- Layout Robusto con Frames ---
        # Marco inferior para el botón
        bottom_frame = ttk.Frame(history_window, padding=(10, 10))
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.history_window_ref = history_window
        clear_button = ttk.Button(bottom_frame, text="Limpiar Historial", 
                                  style='Clear.TButton', command=self._clear_history_and_refresh)
        clear_button.pack()

        # Marco principal para el contenido, se expande para llenar el resto
        main_frame = ttk.Frame(history_window, padding=(10, 10, 10, 0))
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Últimas búsquedas:", font=('Arial', 12, 'bold')).pack(anchor="w", pady=(0, 5))

        history_scroll = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=('Arial', 10), state=tk.DISABLED)
        history_scroll.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # --- Configuración de Estilos (Tags) ---
        history_scroll.tag_configure('history_date', foreground='#666666') # Color gris para la fecha
        history_scroll.tag_configure('history_term', foreground='blue', underline=True)
        history_scroll.tag_bind('history_term', '<Enter>', lambda e: e.widget.config(cursor="hand2"))
        history_scroll.tag_bind('history_term', '<Leave>', lambda e: e.widget.config(cursor=""))

        # --- Llenado de Datos ---
        history_data = self.search_engine.cache.get_history(limit=20)
        history_scroll.config(state=tk.NORMAL)
        history_scroll.delete(1.0, tk.END)

        if not history_data:
            history_scroll.insert(tk.END, "No hay búsquedas en el historial.\n")
        else:
            for i, entry in enumerate(history_data):
                term = entry.get("termino", "Desconocido")
                date_str = datetime.fromisoformat(entry["fecha"]).strftime("%Y-%m-%d %H:%M")
                
                unique_tag = f"hist_item_{i}" # Tag único para el binding del clic
                
                # Insertar fecha con estilo normal/gris
                history_scroll.insert(tk.END, f"[{date_str}] ", 'history_date')
                
                # Insertar término con estilo de link y binding
                history_scroll.insert(tk.END, term, ('history_term', unique_tag))
                history_scroll.insert(tk.END, "\n") # Salto de línea al final

                # Asociar el evento de clic solo al tag único del término
                history_scroll.tag_bind(unique_tag, '<Button-1>', 
                                        lambda e, t=term, hw=history_window: self._select_history_item(t, hw))

        history_scroll.config(state=tk.DISABLED)

        history_window.protocol("WM_DELETE_WINDOW", lambda: self._on_history_close(history_window))

    def _select_history_item(self, term: str, history_window: tk.Toplevel):
        """
        Selecciona un elemento del historial, lo pone en el cuadro de búsqueda y cierra la ventana.
        """
        self.search_var.set(term)
        self._on_history_close(history_window)
        self.on_search()

    def _clear_history_and_refresh(self):
        """
        Limpia el historial y refresca la ventana de historial.
        """
        if messagebox.askyesno("Confirmar", 
                              "¿Estás seguro de que quieres limpiar todo el historial de búsquedas?",
                              parent=self.history_window_ref):
            self.search_engine.cache.clear_cache()
            if hasattr(self, 'history_window_ref') and self.history_window_ref and self.history_window_ref.winfo_exists():
                self.history_window_ref.destroy()
                self.show_history()

    def _on_history_close(self, history_window: tk.Toplevel):
        """
        Maneja el cierre de la ventana de historial.
        """
        history_window.grab_release()
        history_window.destroy()
        self.history_window_ref = None
