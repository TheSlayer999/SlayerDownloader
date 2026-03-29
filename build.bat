@echo off
echo ===================================================
echo     A CRIAR O EXECUTAVEL DO SLAYER DOWNLOADER
echo ===================================================
echo.

echo 1. Instalando o PyInstaller...
"C:\Users\david\AppData\Local\Python\bin\python3.exe" -m pip install pypiwin32 pyinstaller

echo.
echo 2. A compilar o downloader.py num EXE (isso pode demorar uns minutos)...
"C:\Users\david\AppData\Local\Python\bin\python3.exe" -m PyInstaller --noconfirm --onefile --windowed --name "SlayerDownloader" --icon "icon.ico" --add-data "config.json;." "downloader.py"

echo.
echo ===================================================
echo CONCLUIDO! 
echo O teu EXE esta agora disponivel dentro da pasta "dist\"
echo ===================================================
pause
