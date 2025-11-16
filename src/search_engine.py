import json
import os
from typing import List, Dict, Optional
from src.pdf_processor import PDFProcessor, normalize_term
from src.cache_manager import CacheManager

class SearchEngine:
    """
    Orquesta las búsquedas de términos, utilizando el caché y los procesadores de PDF.
    """
    def __init__(self):
        """
        Inicializa el motor de búsqueda, los procesadores de PDF y el gestor de caché.
        Carga los temas predefinidos y el material extra.
        """
        self.nca_processor = PDFProcessor('data/NCA.pdf')
        self.niff_processor = PDFProcessor('data/NIFF.pdf')
        self.cache = CacheManager()
        
        self.predefined_topics: List[str] = []
        self.extra_material_data: Dict = {}
        self._load_topics_and_material()

    def _load_topics_and_material(self):
        """
        Carga los temas predefinidos y la información de material extra desde
        data/temas_principales.json.
        """
        topics_file_path = 'data/temas_principales.json'
        if os.path.exists(topics_file_path):
            try:
                with open(topics_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.predefined_topics = data.get("temas", [])
                    self.extra_material_data = data.get("material_extra", {})
                print(f"[INFO] Temas predefinidos y material extra cargados desde '{topics_file_path}'.")
            except json.JSONDecodeError:
                print(f"[ERROR] Archivo de temas principales corrupto en '{topics_file_path}'.")
            except Exception as e:
                print(f"[ERROR] Error al cargar temas principales desde '{topics_file_path}': {e}")
        else:
            print(f"[ADVERTENCIA] Archivo de temas principales no encontrado en '{topics_file_path}'.")

    def search(self, term: str) -> Dict:
        """
        Busca un término. Primero en caché, luego en PDFs si no se encuentra.
        
        Args:
            term (str): El término a buscar.
            
        Returns:
            Dict: Un diccionario con los resultados de la búsqueda y metadatos.
            {
                'term': str,
                'from_cache': bool,
                'nca_results': List[SearchResult],
                'niff_results': List[SearchResult],
                'material_extra': Dict (info de temas_principales.json)
            }
        """
        print(f"[BÚSQUEDA] Término: '{term}'")
        cached_search = self.cache.get_search(term)
        
        nca_results: List[Dict] = []
        niff_results: List[Dict] = []
        from_cache = False

        if cached_search:
            nca_results = cached_search["resultados"]["NCA"]
            niff_results = cached_search["resultados"]["NIFF"]
            from_cache = True
        else:
            # Realizar búsqueda en PDFs
            print("[PROCESO] Buscando en NCA.pdf...")
            nca_results = self.nca_processor.search_term(term, fuzzy=True)
            print(f"[RESULTADO] NCA: {len(nca_results)} páginas encontradas")

            print("[PROCESO] Buscando en NIFF.pdf...")
            niff_results = self.niff_processor.search_term(term, fuzzy=True)
            print(f"[RESULTADO] NIFF: {len(niff_results)} páginas encontradas")
            
            self.cache.save_search(term, nca_results, niff_results)

        extra_material = self.check_extra_material(term)
        if extra_material['disponible']:
            print("[MATERIAL] ✅ Material extra disponible")
        else:
            print("[MATERIAL] ❌ No hay material extra")

        return {
            'term': term,
            'from_cache': from_cache,
            'nca_results': nca_results,
            'niff_results': niff_results,
            'material_extra': extra_material
        }

    def load_predefined_topics(self) -> List[str]:
        """
        Retorna la lista de temas predefinidos cargados desde el archivo JSON.
        """
        return self.predefined_topics

    def check_extra_material(self, term: str) -> Dict:
        """
        Verifica si existe material extra para el tema.
        
        Args:
            term (str): El término de búsqueda.
            
        Returns:
            Dict: Un diccionario indicando si hay material disponible y los recursos.
            {
                'disponible': bool,
                'recursos': List[str] o None
            }
        """
        normalized_term = normalize_term(term)
        for topic, material in self.extra_material_data.items():
            if normalize_term(topic) == normalized_term:
                return material
        
        return {
            'disponible': False,
            'recursos': []
        }
