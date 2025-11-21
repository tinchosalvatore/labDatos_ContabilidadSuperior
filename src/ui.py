import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import os
import threading
import queue
from datetime import datetime
from typing import List, Dict

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
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("🔍 Buscador de Normas Contables (RT vs NIIF-NIC)")
        self.root.geometry("1200x750")
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

        # --- Sección de Búsqueda ---
        search_frame = ttk.Frame(main_frame, padding="10")
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Temas principales:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.topic_var = tk.StringVar()
        self.topic_combobox = ttk.Combobox(search_frame, textvariable=self.topic_var, values=self.search_engine.load_predefined_topics(), state="readonly", width=40)
        self.topic_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.topic_combobox.set("Selecciona un tema o ingresa uno nuevo")
        
        ttk.Label(search_frame, text="O ingresa tu tema:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.search_entry = ttk.Entry(search_frame, width=40, font=('Arial', 10))
        self.search_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.search_entry.bind("<Return>", lambda event: self.on_search())

        self.search_button = ttk.Button(search_frame, text="BUSCAR", style='Search.TButton', command=self.on_search)
        self.search_button.grid(row=1, column=2, padx=10, pady=5, sticky=tk.E)

        self.history_button = ttk.Button(search_frame, text="HISTORIAL", style='History.TButton', command=self.show_history)
        self.history_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.E)
        
        search_frame.grid_columnconfigure(1, weight=1)

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
        extra_material_frame = ttk.Frame(main_frame, padding="10")
        extra_material_frame.pack(fill=tk.X, pady=5)
        ttk.Label(extra_material_frame, text="📚 Material extra:").pack(side=tk.LEFT, padx=5)
        self.extra_material_label = ttk.Label(extra_material_frame, text="...", font=('Arial', 10, 'bold'))
        self.extra_material_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def setup_text_tags(self):
        for text_widget in [self.rt_text, self.niif_nic_text]:
            text_widget.tag_config('page', foreground='blue', font=('Arial', 9, 'bold'))
            text_widget.tag_config('context', foreground='#666666', font=('Arial', 9, 'italic'))
            text_widget.tag_config('matches', foreground='green', font=('Arial', 9, 'bold'))
            text_widget.tag_config('button', foreground='blue', underline=True)
            text_widget.tag_bind('button', '<Button-1>', self.on_open_pdf_click)
            text_widget.tag_bind('button', '<Enter>', lambda e: e.widget.config(cursor="hand2"))
            text_widget.tag_bind('button', '<Leave>', lambda e: e.widget.config(cursor=""))

    def on_search(self):
        if self.search_in_progress:
            return

        term = self.topic_var.get() if self.topic_var.get() != "Selecciona un tema o ingresa uno nuevo" else self.search_entry.get().strip()
        if not term:
            messagebox.showwarning("Advertencia", "Ingresa un término de búsqueda o selecciona un tema.")
            return

        self.search_in_progress = True
        self.search_button.config(state=tk.DISABLED)
        self.history_button.config(state=tk.DISABLED)

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
        page_num, contexts, matches, pdf_filename = result['page'], result['contexts'], result['matches'], result['pdf_filename']
        
        text_widget.insert(tk.END, f"Página: {page_num} ({pdf_filename}) ", 'page')
        text_widget.insert(tk.END, f"({matches} coincidencias)\n", 'matches')
        
        for context_str in contexts:
            text_widget.insert(tk.END, f"  \"{context_str}\"\n", 'context')
        
        button_text = "📄 Abrir PDF\n\n"
        # Incluir pdf_filename en el tag para identificar el archivo correcto al abrir
        button_tag = f"btn_{column}_{pdf_filename}_{page_num}" 
        text_widget.insert(tk.END, button_text, ('button', button_tag))
        text_widget.tag_bind(button_tag, '<Button-1>', lambda e, c=column, f=pdf_filename, p=page_num: self.open_pdf(c, f, p))

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

    def open_pdf(self, column_key: str, pdf_filename: str, page: int):
        """
        Abre el PDF en la página específica usando webbrowser, ahora compatible con múltiples archivos.
        """
        folder_map = {
            "RT": "rt",
            "NIIF-NIC": "niif_nic"
        }
        
        target_folder = folder_map.get(column_key)
        if not target_folder:
            messagebox.showerror("Error", f"Categoría de PDF desconocida: {column_key}")
            return

        pdf_path = os.path.abspath(os.path.join('data', target_folder, pdf_filename))
        
        if not os.path.exists(pdf_path):
            messagebox.showerror("Error", f"El archivo PDF '{pdf_filename}' no se encontró en '{os.path.join('data', target_folder)}'.")
            return

        url = f'file:///{pdf_path.replace(" ", "%20")}#page={page}'
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el PDF: {e}\nIntenta abrirlo manualmente: {pdf_path}")

    def on_open_pdf_click(self, event):
        # Esta función es un placeholder, el binding se hace directamente en display_single_result
        pass

    def show_history(self):
        """
        Muestra una ventana emergente con el historial de búsquedas.
        """
        if self.search_in_progress: return

        history_window = tk.Toplevel(self.root)
        history_window.title("Historial de Búsquedas")
        history_window.geometry("600x400")
        history_window.transient(self.root)
        history_window.grab_set()

        history_frame = ttk.Frame(history_window, padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar layout con grid para asegurar que el botón sea visible
        history_frame.grid_rowconfigure(0, weight=0) # Para el label "Últimas búsquedas"
        history_frame.grid_rowconfigure(1, weight=1) # Para la lista que se expande
        history_frame.grid_rowconfigure(2, weight=0) # Para el botón de limpiar
        history_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(history_frame, text="Últimas búsquedas:", font=('Arial', 12, 'bold')).grid(row=0, column=0, pady=5, sticky="w")

        list_frame = ttk.Frame(history_frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        
        history_scroll = scrolledtext.ScrolledText(list_frame, wrap=tk.WORD, font=('Arial', 10), height=15)
        history_scroll.pack(fill=tk.BOTH, expand=True) # pack está bien aquí dentro de su propio frame
        
        history_data = self.search_engine.cache.get_history(limit=20)

        if not history_data:
            history_scroll.insert(tk.END, "No hay búsquedas en el historial.\n")
        else:
            for i, entry in enumerate(history_data):
                term = entry.get("termino_original", entry.get("termino", "Desconocido"))
                date_str = datetime.fromisoformat(entry["fecha"]).strftime("%Y-%m-%d %H:%M")
                
                display_text = f"[{date_str}] {term}"
                tag_name = f"hist_{i}"
                
                history_scroll.insert(tk.END, f'{display_text}\n', (tag_name, 'history_item'))
                history_scroll.tag_configure('history_item', foreground='blue', underline=True)
                history_scroll.tag_bind(tag_name, '<Button-1>', 
                                        lambda e, t=term, hw=history_window: self._select_history_item(t, hw))
                history_scroll.tag_bind(tag_name, '<Enter>', lambda e: e.widget.config(cursor="hand2"))
                history_scroll.tag_bind(tag_name, '<Leave>', lambda e: e.widget.config(cursor=""))

        history_scroll.config(state=tk.DISABLED)

        button_frame = ttk.Frame(history_frame)
        button_frame.grid(row=2, column=0, pady=10)
        
        self.history_window_ref = history_window
        clear_button = ttk.Button(button_frame, text="Limpiar Historial", 
                                  style='Clear.TButton', command=self._clear_history_and_refresh)
        clear_button.pack()

        history_window.protocol("WM_DELETE_WINDOW", lambda: self._on_history_close(history_window))

    def _select_history_item(self, term: str, history_window: tk.Toplevel):
        """
        Selecciona un elemento del historial, lo pone en el cuadro de búsqueda y cierra la ventana.
        """
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, term)
        self.topic_combobox.set("Selecciona un tema o ingresa uno nuevo")
        self._on_history_close(history_window)
        self.on_search()

    def _clear_history_and_refresh(self):
        """
        Limpia el historial y refresca la ventana de historial.
        """
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres limpiar todo el historial de búsquedas?"):
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
