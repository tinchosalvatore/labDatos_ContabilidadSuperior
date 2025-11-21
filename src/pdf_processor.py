import fitz  # PyMuPDF
import unicodedata
import sys
import os
import collections
from typing import List, Dict, Optional, Callable, Generator

# Para el manejo de errores en la UI (messagebox)
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    class MockMessagebox:
        def showerror(self, title, message):
            print(f"ERROR: {title} - {message}")
    messagebox = MockMessagebox()
    tk = None


def normalize_term(term: str) -> str:
    """
    Normaliza un término de búsqueda: remueve acentos y convierte a minúsculas.
    """
    if not isinstance(term, str):
        return ""
    nfkd_form = unicodedata.normalize('NFKD', term)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


class PDFProcessor:
    """
    Clase para extraer texto de PDFs y buscar términos.
    """
    def __init__(self, pdf_path: str):
        """
        Inicializa el procesador con la ruta del PDF y analiza los estilos de fuente.
        """
        self.pdf_path = pdf_path
        self.doc: Optional[fitz.Document] = None
        self.toc: List = []
        self.body_font_size: float = 10.0  # Un default razonable

        try:
            self.doc = fitz.open(self.pdf_path)
            self.toc = self.doc.get_toc()
            print(f"[INFO] Cargando PDF: {os.path.basename(pdf_path)} - {self.doc.page_count} páginas")
            print(f"[INFO] Tabla de Contenidos (TOC) encontrada con {len(self.toc)} entradas.")
            self._analyze_font_styles()
        except FileNotFoundError:
            messagebox.showerror("Error de Archivo", f"No se encontró el archivo PDF: {self.pdf_path}")
            sys.exit(1)
        except Exception as e:
            messagebox.showerror("Error de PDF", f"No se pudo leer el PDF '{self.pdf_path}': {str(e)}")
            sys.exit(1)

    def _analyze_font_styles(self, sample_pages: int = 10):
        """
        Analiza las primeras N páginas para determinar el tamaño de fuente del cuerpo principal.
        """
        if not self.doc:
            return

        font_size_counter = collections.Counter()
        num_pages_to_scan = min(sample_pages, self.doc.page_count)

        for page_num in range(num_pages_to_scan):
            page = self.doc.load_page(page_num)
            page_data = page.get_text("dict")
            for block in page_data.get("blocks", []):
                if block['type'] == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = round(span.get('size', 0), 2)
                            count = len(span.get('text', ''))
                            if size > 0 and count > 0:
                                font_size_counter[size] += count
        
        if font_size_counter:
            self.body_font_size = font_size_counter.most_common(1)[0][0]
            print(f"[INFO] Tamaño de fuente principal detectado para '{os.path.basename(self.pdf_path)}': {self.body_font_size}pt")
        else:
            print(f"[ADVERTENCIA] No se pudo determinar el tamaño de fuente principal para '{os.path.basename(self.pdf_path)}'. Usando default: {self.body_font_size}pt")

    def get_total_pages(self) -> int:
        """
        Retorna el número total de páginas del PDF.
        """
        return self.doc.page_count if self.doc else 0

    def extract_text_from_page(self, page_num: int) -> str:
        """
        Extrae texto de una página específica del PDF.
        """
        if self.doc and 0 <= page_num < self.doc.page_count:
            page = self.doc.load_page(page_num)
            return page.get_text("text")
        return ""
    
    def _search_toc(self, term: str) -> Generator[Dict, None, None]:
        """Busca el término en la Tabla de Contenidos del documento."""
        normalized_term = normalize_term(term)
        if not normalized_term:
            return

        for level, title, page in self.toc:
            normalized_title = normalize_term(title)
            if normalized_term in normalized_title:
                yield {
                    'page': page,
                    'contexts': [f"[TOC] {title}"],
                    'matches': 1,
                    'type': 'title'
                }

    def _search_in_page(self, page_num: int, term: str) -> Optional[Dict]:
        """
        Busca un término en una página específica, usando análisis dinámico de fuentes
        para identificar títulos y subtítulos (búsqueda heurística).
        """
        if not self.doc or not (0 <= page_num < self.doc.page_count):
            return None
        
        page = self.doc.load_page(page_num)
        page_data = page.get_text("dict")
        
        normalized_term = normalize_term(term)
        if not normalized_term:
            return None

        contexts = []
        occurrences_count = 0
        max_context_matches = 3
        
        # Heurísticas más estrictas para identificar títulos
        TITLE_FONT_SIZE_MULTIPLIER = 1.20  # Al menos 20% más grande que el cuerpo
        TITLE_MAJORITY_THRESHOLD = 0.8     # 80% de la línea debe ser de tipo título
        TITLE_MAX_LENGTH = 150

        for block in page_data.get("blocks", []):
            if block['type'] == 0:  # 0 for text blocks
                for line in block.get("lines", []):
                    title_char_count = 0
                    total_char_count = 0
                    line_text_parts = []

                    for span in line.get("spans", []):
                        span_text = span.get('text', '')
                        line_text_parts.append(span_text)
                        char_count = len(span_text)
                        total_char_count += char_count

                        is_bold = "bold" in span.get('font', '').lower() or (span.get('flags', 0) & 16)
                        is_large = span.get('size', 0) > (self.body_font_size * TITLE_FONT_SIZE_MULTIPLIER)
                        if is_bold or is_large:
                            title_char_count += char_count
                    
                    full_line_text = "".join(line_text_parts).strip()
                    
                    is_title = (
                        total_char_count > 0 and
                        (title_char_count / total_char_count) >= TITLE_MAJORITY_THRESHOLD and
                        not full_line_text.endswith('.') and
                        len(full_line_text) < TITLE_MAX_LENGTH
                    )
                    
                    if is_title:
                        normalized_line_text = normalize_term(full_line_text)
                        line_occurrences = normalized_line_text.count(normalized_term)
                        
                        if line_occurrences > 0:
                            occurrences_count += line_occurrences
                            if len(contexts) < max_context_matches and full_line_text not in contexts:
                                contexts.append(f"[TÍTULO] {full_line_text}")

        if occurrences_count > 0:
            return {
                'page': page_num + 1,
                'contexts': contexts,
                'matches': occurrences_count,
                'type': 'title'
            }
        return None

    def _search_full_text_in_page(self, page_num: int, term: str) -> Optional[Dict]:
        """Busca un término en el texto completo de una página (fallback)."""
        if not self.doc or not (0 <= page_num < self.doc.page_count):
            return None
            
        page = self.doc.load_page(page_num)
        normalized_term = normalize_term(term)
        if not normalized_term:
            return None

        contexts = []
        matches_count = 0
        max_context_matches = 3
        context_radius = 75

        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            if block[6] == 0: # block_type = 0 for text
                block_text = block[4]
                normalized_block_text = normalize_term(block_text)
                
                if normalized_term in normalized_block_text:
                    matches_count += normalized_block_text.count(normalized_term)
                    
                    if len(contexts) < max_context_matches:
                        try:
                            # Posición aproximada para el contexto
                            pos = normalized_block_text.find(normalized_term)
                            start = max(0, pos - context_radius)
                            end = min(len(block_text), pos + len(normalized_term) + context_radius)
                            context = block_text[start:end].strip().replace('\n', ' ')
                            if context and context not in contexts:
                                contexts.append(f"...{context}...")
                        except Exception:
                            continue
        
        if matches_count > 0:
            return {
                'page': page_num + 1,
                'contexts': contexts,
                'matches': matches_count,
                'type': 'text'
            }
        return None

    def search_term(self, term: str, fuzzy: bool = True) -> List[Dict]:
        """
        Busca un término en todo el PDF. Consume el generador de búsqueda progresiva.
        """
        return list(self.search_term_progressive(term, lambda p: None))

    def _search_full_text_progressive(self, term: str, progress_callback: Callable[[float], None]) -> Generator[Dict, None, None]:
        """Generador para la búsqueda de texto completo (fallback)."""
        total_pages = self.get_total_pages()
        for page_num in range(total_pages):
            result = self._search_full_text_in_page(page_num, term)
            if result:
                yield result
            progress = ((page_num + 1) / total_pages) * 100
            progress_callback(progress)

    def search_term_progressive(self, term: str, progress_callback: Callable[[float], None]) -> Generator[Dict, None, None]:
        """
        Busca un término en el PDF de forma progresiva y por fases:
        1. Tabla de Contenidos (TOC).
        2. Búsqueda heurística de títulos.
        3. Búsqueda de texto completo (si no se encontraron títulos).
        """
        total_pages = self.get_total_pages()
        if total_pages == 0:
            progress_callback(100.0)
            return

        found_title_match = False
        processed_pages = set()
        
        # --- Fase 1: Búsqueda en TOC ---
        for result in self._search_toc(term):
            if not found_title_match:
                print(f"[INFO] Encontradas coincidencias de '{term}' en la Tabla de Contenidos.")
                found_title_match = True
            
            page_index = result['page'] - 1 # TOC es 1-based
            if 0 <= page_index < total_pages:
                processed_pages.add(page_index)
            yield result
        
        # --- Fase 2: Búsqueda Heurística de Títulos ---
        print(f"[INFO] Buscando '{term}' con heurística de títulos...")
        for page_num in range(total_pages):
            if page_num in processed_pages:
                progress = ((page_num + 1) / total_pages) * 100
                progress_callback(progress)
                continue

            result = self._search_in_page(page_num, term)
            if result:
                if not found_title_match:
                    print(f"[INFO] Encontradas coincidencias de '{term}' en títulos del documento.")
                    found_title_match = True
                yield result
            
            progress = ((page_num + 1) / total_pages) * 100
            progress_callback(progress)

        # --- Fase 3: Búsqueda de Texto Completo (Fallback) ---
        if not found_title_match:
            print(f"[INFO] No se encontraron títulos para '{term}'. Realizando búsqueda de texto completo como fallback.")
            yield from self._search_full_text_progressive(term, progress_callback)