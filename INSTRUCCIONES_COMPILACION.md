# Cómo Compilar la Aplicación en un Ejecutable (.exe)

Este documento explica cómo usar los archivos de este proyecto para compilar el buscador en una aplicación de escritorio independiente que se puede ejecutar en Windows sin necesidad de instalar Python.

## Archivos Involucrados

*   `requirements.txt`: Contiene la lista de todas las librerías de Python necesarias, incluyendo `pyinstaller`, la herramienta que usamos para la compilación.
*   `build.spec`: Es el archivo de configuración principal para `PyInstaller`. Le dice qué incluir, cómo nombrar el archivo y otras opciones importantes.
*   `build.bat`: Un script simple para Windows que automatiza el proceso de compilación ejecutando el comando correcto de `PyInstaller`.

## Proceso de Compilación (Paso a Paso)

Sigue estos pasos en la computadora donde quieras compilar el `.exe`. Se recomienda usar Windows para generar un `.exe` compatible.

### 1. Preparar el Entorno

Asegúrate de tener Python instalado en el sistema. Luego, abre una terminal (como `cmd` o `PowerShell`) y navega hasta la carpeta raíz de este proyecto.

### 2. Instalar las Dependencias

Antes de compilar por primera vez, o si las dependencias han cambiado, ejecuta el siguiente comando para instalar todo lo necesario:

```sh
pip install -r requirements.txt
```

### 3. Ejecutar el Script de Compilación

Una vez instaladas las dependencias, simplemente ejecuta el script de compilación haciendo doble clic en el archivo `build.bat`, o ejecutándolo desde la terminal:

```sh
.\build.bat
```

El proceso comenzará y verás muchos mensajes en la terminal. Esto es normal y puede tardar varios minutos.

### 4. Encontrar el Ejecutable

Cuando el proceso termine, se habrán creado dos carpetas nuevas: `build` y `dist`.

**Tu aplicación final se encuentra dentro de la carpeta `dist`**.

Dentro de `dist`, verás una carpeta llamada `BuscadorDeNormas`. Dentro de esa carpeta, encontrarás el archivo `BuscadorDeNormas.exe` junto con otros archivos de los que depende. Para compartir la aplicación, debes comprimir y compartir la carpeta `BuscadorDeNormas` completa.

## Opcional: Compilar en un Único Archivo

Por defecto, el sistema crea una carpeta con el `.exe` y sus dependencias. Esto es más rápido al iniciar y más fácil para depurar.

Si prefieres distribuir un **único archivo `.exe`**, puedes hacerlo. Ten en cuenta que puede tardar un poco más en arrancar. Para ello, puedes editar el script `build.bat` y añadir la opción `--onefile`:

```bat
REM Archivo build.bat modificado
pyinstaller build.spec --onefile
```

Al ejecutar este script modificado, se creará un único archivo `BuscadorDeNormas.exe` en la carpeta `dist`.
