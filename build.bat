@echo off
echo ===================================================
echo         A CRIAR O EXECUTAVEL DO SLAYER HUB
echo ===================================================
echo.

echo 1. Instalando dependencias...
py -m pip install pypiwin32 pyinstaller Pillow pillow-heif yt-dlp

echo.
echo 2. A compilar o downloader.py num EXE (pode demorar uns minutos)...
py -m PyInstaller --noconfirm --onefile --windowed --name "SlayerHub" --icon "assets\icon.ico" --add-data "assets;assets" --hidden-import yt_dlp --hidden-import pillow_heif "downloader.py"

echo.
echo 3. A criar pasta final "SlayerHub"...
if exist "SlayerHub" rd /S /Q "SlayerHub"
mkdir "SlayerHub"
copy /Y "dist\SlayerHub.exe" "SlayerHub\SlayerHub.exe" >nul

echo.
echo ===================================================
echo CONCLUIDO!
echo.
echo A pasta "SlayerHub\" contem tudo pronto:
echo   - SlayerHub.exe
echo.
echo O FFmpeg sera descarregado automaticamente pela app
echo na primeira vez que for necessario.
echo.
echo Podes comprimir esta pasta num .rar para distribuir!
echo ===================================================
pause
