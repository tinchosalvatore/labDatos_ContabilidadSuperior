import json
import os
from typing import List, Dict, Callable
import threading
from src.pdf_processor import PDFProcessor, normalize_term
from src.cache_manager import CacheManager

class SearchEngine:
    """
    Orquesta las búsquedas de términos, utilizando el caché y los procesadores de PDF.
    """
    def __init__(self):
        """
        Inicializa el motor de búsqueda, los procesadores de PDF y el gestor de caché.
        """
        self.rt_processors: Dict[str, PDFProcessor] = self._load_processors('data/rt')
        self.niif_nic_processors: Dict[str, PDFProcessor] = self._load_processors('data/niif_nic')
        self.cache = CacheManager()
        
        self.predefined_topics: List[str] = []
        self.extra_material_data: Dict = {}
        self.indexed_topics: List[Dict] = []
        self.indexed_topics_map: Dict[str, Dict] = {}
        self.indexed_topic_names: List[str] = []

        self._load_topics_and_material()
        self._load_indexed_topics()

    def _load_processors(self, folder_path: str) -> Dict[str, PDFProcessor]:
        """
        Carga todos los archivos PDF de una carpeta y crea un procesador para cada uno.
        """
        processors = {}
        if not os.path.isdir(folder_path):
            print(f"[ADVERTENCIA] El directorio de PDFs no existe: {folder_path}")
            return processors
            
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(folder_path, filename)
                processor = PDFProcessor(pdf_path)
                processors[filename] = processor
        
        print(f"[INFO] Cargados {len(processors)} procesadores desde '{folder_path}'.")
        return processors

    def _load_indexed_topics(self):
        """
        Carga los temas indexados desde data/indice_temas.json.
        """
        index_file_path = 'data/indice_temas.json'
        if os.path.exists(index_file_path):
            try:
                with open(index_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.indexed_topics = data.get("temas", [])
                    # Crear mapa y lista de nombres para acceso rápido
                    self.indexed_topic_names = [normalize_term(topic.get("tema", "")) for topic in self.indexed_topics]
                    for topic in self.indexed_topics:
                        normalized_name = normalize_term(topic.get("tema", ""))
                        if normalized_name:
                            self.indexed_topics_map[normalized_name] = topic
                    
                print(f"[INFO] Temas indexados cargados desde '{index_file_path}'.")
            except json.JSONDecodeError:
                print(f"[ERROR] Archivo de índice de temas corrupto en '{index_file_path}'.")
            except Exception as e:
                print(f"[ERROR] Error al cargar el índice de temas desde '{index_file_path}': {e}")
        else:
            print(f"[ADVERTENCIA] Archivo de índice de temas no encontrado en '{index_file_path}'.")


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

    def _search_indexed_topic(self, term: str) -> Dict:
        """
        Busca un tema que existe en el índice, buscando en los PDFs correspondientes.
        """
        import re
        normalized_term = normalize_term(term)
        topic_data = self.indexed_topics_map.get(normalized_term, {})
        
        rt_results: List[Dict] = []
        niif_nic_results: List[Dict] = []

        print(f"[INDEXADO] Buscando el tema '{term}' usando el índice.")

        for fuente in topic_data.get("fuentes", []):
            ubicacion = fuente.get("ubicacion", "")
            pdf_filename = fuente.get("pdf", "") # p. ej. "Resolución Técnica (RT).pdf"
            if not pdf_filename:
                continue

            # Extraer solo los números de la ubicación para usar como término de búsqueda
            search_numbers = re.findall(r'\d+', ubicacion)
            if not search_numbers:
                continue
            
            search_term = search_numbers[0]
            print(f"[INDEXADO] Ubicación '{ubicacion}' -> Buscando término '{search_term}' en '{pdf_filename}'")
            
            # Encontrar el procesador correcto
            processor: Optional[PDFProcessor] = None
            if pdf_filename in self.rt_processors:
                processor = self.rt_processors[pdf_filename]
            elif pdf_filename in self.niif_nic_processors:
                processor = self.niif_nic_processors[pdf_filename]
            
            if processor:
                results = processor.search_term(search_term, fuzzy=False)
                # Enriquecer resultados con el nombre del archivo y el contexto
                for res in results:
                    res['pdf_filename'] = pdf_filename
                    res['contexts'] = [f"Ubicación para '{term}': {ubicacion}"] + res['contexts']
                
                # Agregar a la lista de resultados correcta
                if pdf_filename in self.rt_processors:
                    rt_results.extend(results)
                else:
                    niif_nic_results.extend(results)
        
        return {
            'rt_results': rt_results,
            'niif_nic_results': niif_nic_results
        }

    def search(self, term: str) -> Dict:
        """
        Busca un término. Prioriza la búsqueda indexada, luego caché, y finalmente PDFs.
        """
        print(f"[BÚSQUEDA] Término: '{term}'")
        normalized_term = normalize_term(term)

        rt_results: List[Dict] = []
        niif_nic_results: List[Dict] = []
        from_cache = False

        # 1. Verificar si es un tema indexado
        if normalized_term in self.indexed_topics_map:
            cached_search = self.cache.get_search(term)
            if cached_search:
                print("[CACHÉ] ✅ Encontrado en caché (indexado)")
                rt_results = cached_search.get("resultados", {}).get("RT", [])
                niif_nic_results = cached_search.get("resultados", {}).get("NIIF-NIC", [])
                from_cache = True
            else:
                print("[CACHÉ] ❌ No encontrado en caché (indexado)")
                indexed_results = self._search_indexed_topic(term)
                rt_results = indexed_results['rt_results']
                niif_nic_results = indexed_results['niif_nic_results']
                self.cache.save_search(term, rt_results, niif_nic_results)
        
        # 2. Si no es indexado, buscar en caché normal
        else:
            cached_search = self.cache.get_search(term)
            if cached_search:
                print("[CACHÉ] ✅ Encontrado en caché (búsqueda normal)")
                rt_results = cached_search.get("resultados", {}).get("RT", [])
                niif_nic_results = cached_search.get("resultados", {}).get("NIIF-NIC", [])
                from_cache = True
            # 3. Si no está en caché, buscar en todos los PDFs
            else:
                print("[CACHÉ] ❌ No encontrado en caché (búsqueda normal)")
                
                print("[PROCESO] Buscando en PDFs de Resolución Técnica (RT)...")
                for filename, processor in self.rt_processors.items():
                    results = processor.search_term(term, fuzzy=True)
                    for res in results:
                        res['pdf_filename'] = filename
                    rt_results.extend(results)
                print(f"[RESULTADO] RT: {len(rt_results)} coincidencias encontradas en {len(self.rt_processors)} archivo(s).")

                print("[PROCESO] Buscando en PDFs de NIIF-NIC...")
                for filename, processor in self.niif_nic_processors.items():
                    results = processor.search_term(term, fuzzy=True)
                    for res in results:
                        res['pdf_filename'] = filename
                    niif_nic_results.extend(results)
                print(f"[RESULTADO] NIIF-NIC: {len(niif_nic_results)} coincidencias encontradas en {len(self.niif_nic_processors)} archivo(s).")

                self.cache.save_search(term, rt_results, niif_nic_results)

        extra_material = self.check_extra_material(term)
        if extra_material.get('disponible'):
            print("[MATERIAL] ✅ Material extra disponible")
        else:
            print("[MATERIAL] ❌ No hay material extra")

        return {
            'term': term,
            'from_cache': from_cache,
            'rt_results': rt_results,
            'niif_nic_results': niif_nic_results,
            'material_extra': extra_material
        }
    
    def _search_indexed_topic_progressive(self, term: str, 
                                          rt_result_callback: Callable[[Dict], None],
                                          niif_nic_result_callback: Callable[[Dict], None]):
        """
        Busca un tema indexado y usa callbacks para los resultados.
        """
        import re
        normalized_term = normalize_term(term)
        topic_data = self.indexed_topics_map.get(normalized_term, {})
        
        print(f"[INDEXADO-PROG] Buscando el tema '{term}' usando el índice.")

        rt_results = []
        niif_nic_results = []

        for fuente in topic_data.get("fuentes", []):
            ubicacion = fuente.get("ubicacion", "")
            pdf_filename = fuente.get("pdf", "")
            if not pdf_filename: continue

            search_numbers = re.findall(r'\d+', ubicacion)
            if not search_numbers: continue
            
            search_term = search_numbers[0]
            print(f"[INDEXADO-PROG] Ubicación '{ubicacion}' -> Buscando término '{search_term}' en '{pdf_filename}'")
            
            processor: Optional[PDFProcessor] = None
            if pdf_filename in self.rt_processors:
                processor = self.rt_processors[pdf_filename]
            elif pdf_filename in self.niif_nic_processors:
                processor = self.niif_nic_processors[pdf_filename]
            
            if processor:
                results = processor.search_term(search_term, fuzzy=False)
                for res in results:
                    res['pdf_filename'] = pdf_filename
                    res['contexts'] = [f"Ubicación para '{term}': {ubicacion}"] + res['contexts']
                    
                    if pdf_filename in self.rt_processors:
                        rt_result_callback(res)
                        rt_results.append(res)
                    else:
                        niif_nic_result_callback(res)
                        niif_nic_results.append(res)
        
        # Guardar en caché después de la búsqueda indexada
        self.cache.save_search(term, rt_results, niif_nic_results)


    def _search_worker(self, processor_name: str, processor: PDFProcessor, term: str, 
                       progress_callback: Callable[[float], None], 
                       result_callback: Callable[[Dict], None]) -> List[Dict]:
        """
        Worker para un thread de búsqueda. Consume el generador y llama a los callbacks.
        Añade el nombre del archivo PDF al resultado.
        """
        results = []
        for result in processor.search_term_progressive(term, progress_callback):
            result['pdf_filename'] = processor_name # Añadir el nombre del archivo PDF
            result_callback(result)
            results.append(result)
        progress_callback(100.0) # Asegurar que la barra llegue al 100%
        return results

    def search_progressive(self, term: str, 
                           rt_progress_callback: Callable[[float], None], 
                           rt_result_callback: Callable[[Dict], None],
                           niif_nic_progress_callback: Callable[[float], None],
                           niif_nic_result_callback: Callable[[Dict], None]):
        """
        Realiza una búsqueda progresiva en paralelo. Prioriza temas indexados.
        """
        print(f"[BÚSQUEDA PROGRESIVA] Término: '{term}'")
        normalized_term = normalize_term(term)
        
        # 1. Verificar caché primero
        cached_search = self.cache.get_search(term)
        if cached_search:
            print("[CACHÉ] ✅ Encontrado en caché (progresivo)")
            rt_results = cached_search.get("resultados", {}).get("RT", [])
            niif_nic_results = cached_search.get("resultados", {}).get("NIIF-NIC", [])
            
            for res in rt_results:
                rt_result_callback(res)
            rt_progress_callback(100.0)
            
            for res in niif_nic_results:
                niif_nic_result_callback(res)
            niif_nic_progress_callback(100.0)
            return
            
        # 2. Si no está en caché, ver si es un tema indexado
        if normalized_term in self.indexed_topics_map:
            print("[INDEXADO] Buscando tema indexado de forma progresiva.")
            self._search_indexed_topic_progressive(term, rt_result_callback, niif_nic_result_callback)
            # Marcar el progreso como completo para ambos
            rt_progress_callback(100.0)
            niif_nic_progress_callback(100.0)
            
            # Recargar resultados del caché para asegurar que estén completos si el tema indexado se procesó parcialmente
            # en _search_indexed_topic_progressive.
            # Esto es un workaround si no se puede garantizar que el callback progresivo envíe todo
            # y el caché tiene la versión final.
            final_cached_search = self.cache.get_search(term)
            if final_cached_search:
                print("[CACHÉ] ✅ Recuperando resultados finales de tema indexado del caché.")
                for res in final_cached_search.get("resultados", {}).get("RT", []):
                    rt_result_callback(res)
                for res in final_cached_search.get("resultados", {}).get("NIIF-NIC", []):
                    niif_nic_result_callback(res)
            return

        # 3. Si no es indexado ni está en caché, realizar búsqueda en vivo en todos los PDFs
        print("[CACHÉ] ❌ No encontrado, realizando búsqueda en vivo en múltiples PDFs...")
        
        threads = []
        all_rt_results_live: List[Dict] = []
        all_niif_nic_results_live: List[Dict] = []

        # Función auxiliar para agregar resultados
        def rt_collector_callback(result: Dict):
            all_rt_results_live.append(result)
            rt_result_callback(result)
        
        def niif_nic_collector_callback(result: Dict):
            all_niif_nic_results_live.append(result)
            niif_nic_result_callback(result)

        # Lanzar threads para cada procesador RT
        for filename, processor in self.rt_processors.items():
            thread = threading.Thread(target=self._search_worker, 
                                      args=(filename, processor, term, rt_progress_callback, rt_collector_callback))
            threads.append(thread)
            thread.start()

        # Lanzar threads para cada procesador NIIF-NIC
        for filename, processor in self.niif_nic_processors.items():
            thread = threading.Thread(target=self._search_worker, 
                                      args=(filename, processor, term, niif_nic_progress_callback, niif_nic_collector_callback))
            threads.append(thread)
            thread.start()

        # Esperar a que todos los threads terminen
        for thread in threads:
            thread.join()

        # Asegurar que las barras de progreso lleguen al 100% si algún worker falló o no actualizó.
        rt_progress_callback(100.0)
        niif_nic_progress_callback(100.0)
        
        # Guardar en caché después de que todas las búsquedas hayan terminado
        self.cache.save_search(term, all_rt_results_live, all_niif_nic_results_live)

    def load_predefined_topics(self) -> List[str]:
        """
        Retorna la lista de temas predefinidos para la UI.
        Prioriza los temas del nuevo índice y añade los de la configuración antigua si no existen.
        """
        # Extraer los nombres originales de los temas indexados para la UI
        indexed_display_names = [topic.get("tema", "") for topic in self.indexed_topics]
        
        # Combinar con temas predefinidos antiguos, evitando duplicados
        combined_topics = indexed_display_names
        for topic in self.predefined_topics:
            if topic not in combined_topics:
                combined_topics.append(topic)
                
        return sorted(list(filter(None, combined_topics)))

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
