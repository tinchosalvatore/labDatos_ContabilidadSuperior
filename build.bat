@echo off
echo Iniciando la compilacion con PyInstaller...
echo Esto puede tardar varios minutos. Por favor, espera.
echo.

REM Ejecuta PyInstaller usando el archivo de especificacion.
pyinstaller build.spec

echo.
echo ------------------------------------------------------------------
echo Compilacion finalizada.
echo.
echo El programa se encuentra en la carpeta: dist/BuscadorDeNormas
echo ------------------------------------------------------------------
echo.
pause
