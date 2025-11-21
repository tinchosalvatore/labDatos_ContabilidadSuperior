import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import uuid
from src.pdf_processor import normalize_term # Importar la función de normalización de busquedas, de un archivo local

class CacheManager:
    """
    Gestiona el archivo cache_busquedas.json para almacenar y recuperar búsquedas.
    """
    def __init__(self, cache_path: str = 'data/cache_busquedas.json'):
        """
        Inicializa el gestor de caché.
        Carga el caché existente o crea un archivo vacío si no existe o está corrupto.
        """
        self.cache_path = cache_path
        self.cache_data: Dict = {"busquedas": []}
        self._load_cache()

    def _load_cache(self):
        """
        Carga los datos del caché desde el archivo JSON.
        Si el archivo no existe o está corrupto, inicializa un caché vacío.
        """
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                # Asegurarse de que 'busquedas' sea una lista
                if not isinstance(self.cache_data.get("busquedas"), list):
                    print(f"[ADVERTENCIA] El caché en '{self.cache_path}' tiene un formato incorrecto. Reiniciando caché.")
                    self.cache_data = {"busquedas": []}
            except json.JSONDecodeError:
                print(f"[ADVERTENCIA] Archivo de caché corrupto en '{self.cache_path}'. Reiniciando caché.")
                self.cache_data = {"busquedas": []}
            except Exception as e:
                print(f"[ERROR] Error al cargar el caché desde '{self.cache_path}': {e}. Reiniciando caché.")
                self.cache_data = {"busquedas": []}
        else:
            print(f"[INFO] Archivo de caché no encontrado en '{self.cache_path}'. Creando uno nuevo.")
            self._save_cache() # Crear el archivo vacío

    def _save_cache(self):
        """
        Guarda los datos actuales del caché en el archivo JSON.
        """
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Error al guardar el caché en '{self.cache_path}': {e}")

    def get_search(self, term: str) -> Optional[Dict]:
        """
        Busca si un término ya fue procesado en el caché.
        Normaliza el término (lowercase, sin acentos) antes de buscar.
        
        Args:
            term (str): El término de búsqueda.
            
        Returns:
            Optional[Dict]: El resultado de la búsqueda cacheada o None si no se encuentra.
        """
        normalized_term = normalize_term(term)
        for search_entry in self.cache_data.get("busquedas", []):
            if normalize_term(search_entry.get("termino", "")) == normalized_term:
                print(f"[CACHÉ] ✅ Encontrado en caché para el término: '{term}'")
                return search_entry
        print(f"[CACHÉ] ❌ No encontrado en caché para el término: '{term}'")
        return None

    def save_search(self, term: str, rt_results: List, niif_nic_results: List):
        """
        Guarda una nueva búsqueda en el caché.
        
        Args:
            term (str): El término de búsqueda original.
            rt_results (List): Lista de resultados de búsqueda para Resolución Técnica (RT).
            niif_nic_results (List): Lista de resultados de búsqueda para NIIF-NIC.
        """
        # Eliminar búsquedas antiguas del mismo término para mantener solo la más reciente
        normalized_term = normalize_term(term)
        self.cache_data["busquedas"] = [
            s for s in self.cache_data["busquedas"] 
            if normalize_term(s.get("termino", "")) != normalized_term
        ]

        new_search_entry = {
            "id": str(uuid.uuid4()),
            "termino": term,
            "fecha": datetime.now().isoformat(),
            "resultados": {
                "RT": rt_results,
                "NIIF-NIC": niif_nic_results
            }
        }
        self.cache_data["busquedas"].append(new_search_entry)
        self._save_cache()
        print(f"[CACHÉ] ✅ Guardado para futuras búsquedas: '{term}'")

    def get_history(self, limit: int = 7) -> List[Dict]:
        """
        Retorna las últimas N búsquedas ordenadas por fecha (más recientes primero).
        
        Args:
            limit (int): El número máximo de búsquedas a retornar.
            
        Returns:
            List[Dict]: Una lista de las búsquedas más recientes.
        """
        # Ordenar por fecha descendente
        sorted_history = sorted(
            self.cache_data.get("busquedas", []),
            key=lambda x: x.get("fecha", ""),
            reverse=True
        )
        return sorted_history[:limit]

    def clear_cache(self):
        """
        Elimina todo el historial de búsquedas del caché.
        """
        self.cache_data = {"busquedas": []}
        self._save_cache()
        print("[CACHÉ] Historial de búsquedas limpiado.")