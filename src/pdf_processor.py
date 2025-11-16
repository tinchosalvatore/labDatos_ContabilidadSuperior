import fitz  # PyMuPDF
import unicodedata
import sys
import os
from typing import List, Dict, Optional
from rapidfuzz import fuzz

# Para el manejo de errores en la UI (messagebox)
# Aunque messagebox es parte de tkinter, lo importamos aquí para el manejo de errores críticos
# que podrían ocurrir antes de que la UI esté completamente inicializada.
# En un entorno real, esto podría ser un logger o un mecanismo de reporte de errores.
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    # Fallback si tkinter no está disponible (ej. en un entorno sin GUI)
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
        Inicializa el procesador con la ruta del PDF.
        Abre el documento PDF y maneja posibles errores.
        """
        self.pdf_path = pdf_path
        self.doc: Optional[fitz.Document] = None
        try:
            self.doc = fitz.open(self.pdf_path)
            print(f"[INFO] Cargando PDF: {os.path.basename(pdf_path)} - {self.doc.page_count} páginas")
        except FileNotFoundError:
            messagebox.showerror("Error de Archivo", f"No se encontró el archivo PDF: {self.pdf_path}")
            sys.exit(1)
        except Exception as e:
            messagebox.showerror("Error de PDF", f"No se pudo leer el PDF '{self.pdf_path}': {str(e)}")
            sys.exit(1)

    def get_total_pages(self) -> int:
        """
        Retorna el número total de páginas del PDF.
        """
        if self.doc:
            return self.doc.page_count
        return 0

    def extract_text_from_page(self, page_num: int) -> str:
        """
        Extrae texto de una página específica del PDF.
        Las páginas son 0-indexadas en PyMuPDF, pero la UI las mostrará 1-indexadas.
        """
        if self.doc and 0 <= page_num < self.doc.page_count:
            page = self.doc.load_page(page_num)
            return page.get_text("text")
        return ""
    
    def _extract_context(self, text: str, start_pos: int, end_pos: int, buffer: int = 75) -> str:
        """
        Extrae un fragmento de texto (contexto) alrededor de una coincidencia.
        """
        start = max(0, start_pos - buffer)
        end = min(len(text), end_pos + buffer)
        return text[start:end].replace('\n', ' ').strip() # Reemplazar saltos de línea para mejor visualización

    def _search_in_page(self, page_num: int, term: str, fuzzy: bool = True) -> Optional[Dict]:
        """
        Busca un término en una página específica y retorna los resultados.
        Método auxiliar para search_term y search_term_progressive.
        """
        page_text = self.extract_text_from_page(page_num)
        if not page_text:
            return None

        normalized_page_text = normalize_term(page_text)
        normalized_term = normalize_term(term)
        
        matches_on_page = []
        occurrences_count = 0
        
        if not normalized_term: # Evitar buscar términos vacíos
            return None

        # Límite de 3 coincidencias por página para mostrar contexto.
        # El conteo total de coincidencias 'matches' en el diccionario aún puede ser mayor.
        max_context_matches = 3 

        if fuzzy:
            # Buscar coincidencias difusas
            # Iteramos para encontrar múltiples ocurrencias y sus contextos
            i = 0
            while i < len(normalized_page_text) and len(matches_on_page) < max_context_matches:
                # Busca el término exacto normalizado como primera opción.
                start_idx_normalized = normalized_page_text.find(normalized_term, i)
                if start_idx_normalized != -1:
                    # Encontró el término exacto normalizado
                    match_in_normalized = True
                    target_normalized = normalized_term
                    current_match_start = start_idx_normalized
                    current_match_end = start_idx_normalized + len(normalized_term)
                else:
                    # Si no se encuentra un match exacto, proceder con fuzzy matching en substrings del original.
                    # Esto es computacionalmente intensivo, pero necesario para `partial_ratio` sin posición.
                    # Para evitar el exceso de cómputo, solo revisamos substrings de longitud similar.
                    
                    # Intentar encontrar si una subcadena del texto de la página
                    # coincide "fuzzily" con el término normalizado.
                    
                    # Iterar sobre las posibles posiciones de inicio del término.
                    # Considerar un rango de longitudes para el substring a comparar, 
                    # centrado en la longitud del término normalizado.
                    # Ejemplo: longitud del término +/- 20%
                    
                    len_norm_term = len(normalized_term)
                    min_len_check = max(1, int(len_norm_term * 0.8))
                    max_len_check = int(len_norm_term * 1.2) + 1
                    
                    best_ratio_for_fuzzy_sub = 0
                    fuzzy_sub_start = -1
                    fuzzy_sub_end = -1
                    
                    for k in range(i, len(normalized_page_text)):
                        for sub_len in range(min_len_check, max_len_check):
                            if k + sub_len > len(normalized_page_text):
                                continue
                            
                            subtext_to_compare = normalized_page_text[k:k+sub_len]
                            current_ratio = fuzz.partial_ratio(subtext_to_compare, normalized_term)
                            
                            if current_ratio > best_ratio_for_fuzzy_sub:
                                best_ratio_for_fuzzy_sub = current_ratio
                                fuzzy_sub_start = k
                                fuzzy_sub_end = k + sub_len
                    
                    if best_ratio_for_fuzzy_sub >= 80 and fuzzy_sub_start != -1:
                        match_in_normalized = True
                        target_normalized = normalized_page_text[fuzzy_sub_start:fuzzy_sub_end]
                        current_match_start = fuzzy_sub_start
                        current_match_end = fuzzy_sub_end
                    else:
                        match_in_normalized = False

                if match_in_normalized:
                    occurrences_count += 1
                    if len(matches_on_page) < max_context_matches:
                        # Hay que encontrar la posición en el texto original. Esto es un hack.
                        # Asumimos que la posición en el texto normalizado se traslada directamente.
                        context_start = current_match_start
                        context_end = current_match_end
                        
                        context = self._extract_context(page_text, context_start, context_end)
                        matches_on_page.append({
                            'context': context
                        })
                    
                    # Avanzar el índice para no detectar la misma coincidencia inmediatamente
                    i = current_match_end # Avanzar al final del match encontrado
                else:
                    # Si no hubo match (ni exacto ni fuzzy), avanzar un poco para evitar loops infinitos
                    # Si el término es muy corto, avanzar 1. Si es más largo, avanzar por su longitud.
                    advance = max(1, len(normalized_term) // 2)
                    i += advance

        else: # Búsqueda exacta (case-insensitive, accent-insensitive)
            # Find all occurrences of the normalized term in the normalized page text
            start_idx_normalized = 0
            while True:
                start_idx_normalized = normalized_page_text.find(normalized_term, start_idx_normalized)
                if start_idx_normalized == -1:
                    break
                
                occurrences_count += 1
                if len(matches_on_page) < max_context_matches:
                    end_idx_normalized = start_idx_normalized + len(normalized_term)
                    context = self._extract_context(page_text, start_idx_normalized, end_idx_normalized)
                    matches_on_page.append({
                        'context': context
                    })
                
                start_idx_normalized += len(normalized_term)

        if occurrences_count > 0:
            return {
                'page': page_num + 1,  # Las páginas son 1-indexadas para el usuario
                'contexts': [m['context'] for m in matches_on_page], # List of contexts
                'matches': occurrences_count
            }
        return None

    def search_term(self, term: str, fuzzy: bool = True) -> List[Dict]:
        """
        Busca un término en todo el PDF.
        
        Args:
            term (str): El término a buscar.
            fuzzy (bool): Si la búsqueda debe ser difusa.
            
        Returns:
            List[Dict]: Lista de SearchResult con estructura:
            {
                'page': int,
                'contexts': List[str] (hasta 3 contextos alrededor del término),
                'matches': int (número total de coincidencias en esa página)
            }
        """
        all_results: List[Dict] = []
        total_pages = self.get_total_pages()
        for page_num in range(total_pages):
            result = self._search_in_page(page_num, term, fuzzy)
            if result:
                all_results.append(result)
        return all_results

    def search_term_progressive(self, term: str, callback) -> None:
        """
        Busca un término en todo el PDF de forma progresiva, llamando a un callback
        por cada página procesada que contenga resultados.

        Args:
            term (str): El término a buscar.
            callback (callable): Función a llamar con (page_num, result) si se encuentran coincidencias.
                                 'result' es el mismo diccionario retornado por _search_in_page.
        """
        total_pages = self.get_total_pages()
        for page_num in range(total_pages):
            result = self._search_in_page(page_num, term, True) # Siempre fuzzy para progresiva? O configurable?
            if result:
                callback(page_num + 1, result) # Manda page_num 1-indexado