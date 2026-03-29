@echo off
echo ===================================================
echo     A CRIAR O EXECUTAVEL DO SLAYER DOWNLOADER
echo ===================================================
echo.

echo 1. Instalando dependencias...
"C:\Users\david\AppData\Local\Python\bin\python3.exe" -m pip install pypiwin32 pyinstaller

echo.
echo 2. A compilar o downloader.py num EXE (isso pode demorar uns minutos)...
"C:\Users\david\AppData\Local\Python\bin\python3.exe" -m PyInstaller --noconfirm --onefile --windowed --name "SlayerDownloader" --icon "assets\icon.ico" --add-data "assets;assets" "downloader.py"

echo.
echo 3. A copiar ficheiros necessarios para a pasta dist...
if exist "ffmpeg.exe" (
    copy /Y "ffmpeg.exe" "dist\ffmpeg.exe" >nul
    echo    FFmpeg copiado para dist\
) else (
    echo    AVISO: ffmpeg.exe nao encontrado! Coloca-o na pasta raiz do projeto.
)

echo.
echo ===================================================
echo CONCLUIDO! 
echo O teu EXE esta agora disponivel dentro da pasta "dist\"
echo Basta abrir o SlayerDownloader.exe e usar!
echo ===================================================
pause
