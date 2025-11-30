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
        
        self.extra_material_data: Dict = {}
        self.indexed_topics: List[Dict] = []
        self.indexed_topics_map: Dict[str, Dict] = {}
        self.indexed_topic_names: List[str] = []

        self._load_indexed_topics()
        self._load_extra_material()

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


    def _load_extra_material(self):
        """
        Carga la información de material extra desde data/material_extra.json.
        """
        material_file_path = 'data/material_extra.json'
        if os.path.exists(material_file_path):
            try:
                with open(material_file_path, 'r', encoding='utf-8') as f:
                    self.extra_material_data = json.load(f)
                print(f"[INFO] Material extra cargado desde '{material_file_path}'.")
            except json.JSONDecodeError:
                print(f"[ERROR] Archivo de material extra corrupto en '{material_file_path}'.")
            except Exception as e:
                print(f"[ERROR] Error al cargar material extra desde '{material_file_path}': {e}")
        else:
            print(f"[ADVERTENCIA] Archivo de material extra no encontrado en '{material_file_path}'.")

    def _search_indexed_topic(self, term: str) -> Dict:
        """
        Procesa un tema del índice. Si tiene página, crea un resultado directo.
        Si la página es nula, realiza una búsqueda de texto de respaldo en el PDF correcto.
        """
        import re
        normalized_term = normalize_term(term)
        topic_data = self.indexed_topics_map.get(normalized_term, {})
        
        rt_results: List[Dict] = []
        niif_nic_results: List[Dict] = []

        print(f"[INDEXADO] Procesando tema '{term}' desde el índice.")

        for fuente in topic_data.get("fuentes", []):
            pdf_filename = fuente.get("pdf")
            page = fuente.get("pagina")
            ubicacion = fuente.get("ubicacion", "")

            if not pdf_filename:
                continue

            # Encontrar el procesador correcto (RT o NIIF-NIC)
            processor: 'PDFProcessor' = None
            is_rt = False
            if pdf_filename in self.rt_processors:
                processor = self.rt_processors[pdf_filename]
                is_rt = True
            elif pdf_filename in self.niif_nic_processors:
                processor = self.niif_nic_processors[pdf_filename]
            
            if not processor:
                print(f"[ADVERTENCIA] No se encontró procesador para el PDF '{pdf_filename}' del índice.")
                continue
            
            # --- Lógica Principal: Enlace Directo o Búsqueda de Respaldo ---
            if isinstance(page, int): # Caso 1: Tenemos un número de página específico.
                print(f"[INDEXADO] ✅ Enlace directo a página {page} en '{pdf_filename}'.")
                result = {
                    'pdf_filename': pdf_filename,
                    'page': page,
                    'context': f"Fuente: {fuente.get('norma', 'N/A')}\nUbicación Original: {ubicacion}",
                    'matches': 1
                }
                if is_rt:
                    rt_results.append(result)
                else:
                    niif_nic_results.append(result)
            elif page == "todo el pdf": # Caso 2: El tema abarca todo el PDF.
                print(f"[INDEXADO] ✅ Enlace directo a PDF completo: '{pdf_filename}'.")
                result = {
                    'pdf_filename': pdf_filename,
                    'page': "todo el pdf", # Almacenar el string para que la UI lo interprete
                    'context': f"Fuente: {fuente.get('norma', 'N/A')}\nUbicación Original: {ubicacion} (PDF completo)",
                    'matches': 1
                }
                if is_rt:
                    rt_results.append(result)
                else:
                    niif_nic_results.append(result)
            else: # Caso 3: page is None. Realizar búsqueda de texto de respaldo.
                # Se busca el primer número en 'ubicacion' (p. ej. párrafo) o el nombre del tema.
                search_numbers = re.findall(r'\d+', ubicacion)
                search_query = search_numbers[0] if search_numbers else term
                
                print(f"[INDEXADO] 🟡 Página nula. Buscando '{search_query}' en '{pdf_filename}' como respaldo.")
                
                # Usamos la búsqueda por texto normal, pero solo en este PDF.
                fallback_results = processor.search_term(search_query, fuzzy=False)
                
                for res in fallback_results:
                    res['pdf_filename'] = pdf_filename
                    res['contexts'] = [f"Respaldo para: '{ubicacion}'"] + res['contexts']
                
                if is_rt:
                    rt_results.extend(fallback_results)
                else:
                    niif_nic_results.extend(fallback_results)

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

        # 1. Verificar caché (para cualquier tipo de búsqueda)
        cached_search = self.cache.get_search(term)
        if cached_search:
            print("[CACHÉ] ✅ Encontrado en caché")
            rt_results = cached_search.get("resultados", {}).get("RT", [])
            niif_nic_results = cached_search.get("resultados", {}).get("NIIF-NIC", [])
            from_cache = True
        
        # 2. Si no está en caché, decidir qué tipo de búsqueda realizar
        else:
            print("[CACHÉ] ❌ No encontrado en caché")
            # 2.1 Si es un tema indexado, usar el método de consulta directa
            if normalized_term in self.indexed_topics_map:
                indexed_results = self._search_indexed_topic(term)
                rt_results = indexed_results['rt_results']
                niif_nic_results = indexed_results['niif_nic_results']
            
            # 2.2 Si no, realizar la búsqueda por texto completo en los PDFs
            else:
                print("[PROCESO] El término no es un tema principal. Realizando búsqueda por texto completo...")
                print("[PROCESO] Buscando en PDFs de Resolución Técnica (RT)...")
                for filename, processor in self.rt_processors.items():
                    results = processor.search_term(term, fuzzy=True)
                    for res in results:
                        res['pdf_filename'] = filename
                    rt_results.extend(results)
                print(f"[RESULTADO] RT: {len(rt_results)} coincidencias encontradas.")

                print("[PROCESO] Buscando en PDFs de NIIF-NIC...")
                for filename, processor in self.niif_nic_processors.items():
                    results = processor.search_term(term, fuzzy=True)
                    for res in results:
                        res['pdf_filename'] = filename
                    niif_nic_results.extend(results)
                print(f"[RESULTADO] NIIF-NIC: {len(niif_nic_results)} coincidencias encontradas.")

            # 3. Guardar los nuevos resultados en el caché
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
        Procesa un tema indexado de forma progresiva. Para páginas nulas,
        delega en el buscador progresivo de texto del procesador correspondiente.
        """
        import re
        normalized_term = normalize_term(term)
        topic_data = self.indexed_topics_map.get(normalized_term, {})
        
        print(f"[INDEXADO-PROG] Procesando tema '{term}' desde el índice.")

        # Se usan para guardar en caché al final
        rt_results_for_cache: List[Dict] = []
        niif_nic_results_for_cache: List[Dict] = []

        for fuente in topic_data.get("fuentes", []):
            pdf_filename = fuente.get("pdf")
            page = fuente.get("pagina")
            ubicacion = fuente.get("ubicacion", "")

            if not pdf_filename: continue

            processor: 'PDFProcessor' = None
            is_rt = False
            if pdf_filename in self.rt_processors:
                processor = self.rt_processors[pdf_filename]
                is_rt = True
            elif pdf_filename in self.niif_nic_processors:
                processor = self.niif_nic_processors[pdf_filename]
            
            if not processor: continue

            if isinstance(page, int): # Caso 1: Enlace directo a página específica.
                print(f"[INDEXADO-PROG] ✅ Enlace directo a página {page} en '{pdf_filename}'.")
                result = {
                    'pdf_filename': pdf_filename,
                    'page': page,
                    'context': f"Fuente: {fuente.get('norma', 'N/A')}\nUbicación Original: {ubicacion}",
                    'matches': 1
                }
                if is_rt:
                    rt_result_callback(result)
                    rt_results_for_cache.append(result)
                else:
                    niif_nic_result_callback(result)
                    niif_nic_results_for_cache.append(result)
            elif page == "todo el pdf": # Caso 2: El tema abarca todo el PDF.
                print(f"[INDEXADO-PROG] ✅ Enlace directo a PDF completo: '{pdf_filename}'.")
                result = {
                    'pdf_filename': pdf_filename,
                    'page': "todo el pdf", # Almacenar el string para que la UI lo interprete
                    'context': f"Fuente: {fuente.get('norma', 'N/A')}\nUbicación Original: {ubicacion} (PDF completo)",
                    'matches': 1
                }
                if is_rt:
                    rt_result_callback(result)
                    rt_results_for_cache.append(result)
                else:
                    niif_nic_result_callback(result)
                    niif_nic_results_for_cache.append(result)
            else: # Caso 3: page is None. Búsqueda de respaldo progresiva.
                search_numbers = re.findall(r'\d+', ubicacion)
                search_query = search_numbers[0] if search_numbers else term
                print(f"[INDEXADO-PROG] 🟡 Página nula. Buscando '{search_query}' en '{pdf_filename}'.")

                # El callback de progreso no es relevante aquí, se maneja a nivel superior.
                def dummy_progress_callback(val): pass

                for res in processor.search_term_progressive(search_query, dummy_progress_callback):
                    res['pdf_filename'] = pdf_filename
                    res['contexts'] = [f"Respaldo para: '{ubicacion}'"] + res['contexts']
                    
                    if is_rt:
                        rt_result_callback(res)
                        rt_results_for_cache.append(res)
                    else:
                        niif_nic_result_callback(res)
                        niif_nic_results_for_cache.append(res)
        
        # Guardar en caché el conjunto completo de resultados al final
        self.cache.save_search(term, rt_results_for_cache, niif_nic_results_for_cache)


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
            self._search_indexed_topic_progressive(term, rt_result_callback, niif_nic_result_callback)
            # Marcar el progreso como completo para ambos, ya que es instantáneo
            rt_progress_callback(100.0)
            niif_nic_progress_callback(100.0)
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

        # Asegurar que las barras de progreso lleguen al 100%
        rt_progress_callback(100.0)
        niif_nic_progress_callback(100.0)
        
        # Guardar en caché después de que todas las búsquedas hayan terminado
        self.cache.save_search(term, all_rt_results_live, all_niif_nic_results_live)

    def load_predefined_topics(self) -> List[str]:
        """
        Retorna la lista de temas para la UI, extraídos únicamente desde el índice.
        """
        # Extraer los nombres originales de los temas indexados para la UI
        indexed_display_names = [topic.get("tema", "") for topic in self.indexed_topics]
        return sorted(list(filter(None, indexed_display_names)))

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
        # El diccionario de material extra ahora tiene los temas como claves principales
        for topic_key, material in self.extra_material_data.items():
            if normalize_term(topic_key) == normalized_term:
                return material
        
        return {
            'disponible': False,
            'recursos': []
        }
