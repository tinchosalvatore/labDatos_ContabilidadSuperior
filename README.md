# Laboratorio de Datos - Contabilidad Superior
### Facultad de Ciencias Economicas UNCUYO
---
# 🔍 Buscador de Normas Contables NCA/NIFF

## Descripción

Herramienta para buscar y comparar temas contables entre las **Normas Contables Argentinas (NCA)** y las **Normas Internacionales de Información Financiera (NIFF)**.

Permite localizar rápidamente en qué páginas de cada norma se encuentra un tema específico, y además indica si existe material complementario disponible (libros, presentaciones, etc.).

---

## 📋 Características

- ✅ **Búsqueda por temas predefinidos**: Selecciona de una lista de temas principales
- ✅ **Búsqueda libre**: Ingresa cualquier término si no está en la lista
- ✅ **Comparación lado a lado**: Visualiza NCA y NIFF simultáneamente
- ✅ **Apertura directa**: Haz clic para abrir el PDF en la página exacta
- ✅ **Historial de búsquedas**: Revisa tus consultas anteriores
- ✅ **Material extra**: Identifica recursos complementarios disponibles

---

## 🚀 Instalación

### Requisitos previos
- Python 3.8 o superior
- Sistema operativo: Windows, macOS o Linux

### Pasos de instalación

1. **Descargar el proyecto**
   - Descarga y descomprime el archivo ZIP del proyecto

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Colocar los PDFs**
   - Coloca los archivos PDF de las normas en la carpeta `data/`:
     - `NCA.pdf` (Normas Contables Argentinas)
     - `NIFF.pdf` (Normas Internacionales)

---

## 📖 Uso

### Iniciar la aplicación

```bash
python main.py
```

### Interfaz principal

La aplicación mostrará dos columnas:

```
┌─────────────────────────────────────────────┐
│           🔍 Búsqueda de Temas              │
│                                             │
│  [Dropdown: Temas principales ▼]           │
│  O ingresa tu tema: [_______________]      │
│                                             │
│           [  BUSCAR  ]                     │
└─────────────────────────────────────────────┘

┌──────────────────┬──────────────────────────┐
│       NCA        │         NIFF             │
├──────────────────┼──────────────────────────┤
│  Resultados...   │   Resultados...          │
│                  │                          │
│  📄 Página 23    │   📄 Página 45           │
│  [Abrir PDF]     │   [Abrir PDF]            │
└──────────────────┴──────────────────────────┘

📚 Material extra: ✅ Disponible / ❌ No disponible
```

### Ejemplo de uso

1. **Selecciona un tema** del menú desplegable (ej: "Activos Intangibles")
2. **O escribe** un tema personalizado (ej: "depreciación")
3. **Presiona "BUSCAR"**
4. **Visualiza** los resultados en ambas columnas
5. **Haz clic** en "Abrir PDF" para ir directo a la página

---

## 🗂️ Estructura de archivos

```
proyecto/
│
├── main.py                    # Archivo principal para ejecutar
├── requirements.txt           # Dependencias de Python
├── README.md                  # Este archivo
│
├── data/                      # Carpeta de datos
│   ├── NCA.pdf               # Norma Argentina (colocar aquí)
│   ├── NIFF.pdf              # Norma Internacional (colocar aquí)
│   ├── cache_busquedas.json  # Caché (se crea automáticamente)
│   └── temas_principales.json # Lista de temas predefinidos
│
└── src/                       # Código fuente
    ├── pdf_processor.py
    ├── cache_manager.py
    ├── search_engine.py
    └── ui.py
```

---

## ⚙️ Configuración avanzada

### Agregar temas predefinidos

Edita el archivo `data/temas_principales.json`:

```json
{
  "temas": [
    "Activos Intangibles",
    "Instrumentos Financieros",
    "Arrendamientos",
    "Tu nuevo tema aquí"
  ]
}
```

### Agregar material extra

Edita la sección `material_extra` en el mismo archivo:

```json
{
  "material_extra": {
    "Activos Intangibles": {
      "disponible": true,
      "recursos": ["Libro: Contabilidad Avanzada, Cap. 5", "PPT: Tema_3.pptx"]
    }
  }
}
```

---

## 🐛 Solución de problemas

### La aplicación no encuentra los PDFs
- Verifica que los archivos estén en `data/` con los nombres exactos: `NCA.pdf` y `NIFF.pdf`

### El PDF no se abre automáticamente
- Tu navegador predeterminado debe soportar PDFs
- Alternativa: copia la ruta que aparece en pantalla y ábrela manualmente

### La búsqueda es lenta
- La primera búsqueda de cada término indexa los PDFs (puede tardar)
- Búsquedas posteriores del mismo término serán instantáneas

---

## 📞 Soporte

Para consultas académicas sobre el proyecto, contactar a [tu información de contacto].

---

## 📄 Licencia

Este es un proyecto académico para la Facultad de Economía.
Uso educativo únicamente.
