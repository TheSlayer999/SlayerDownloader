@echo off
echo ===================================================
echo     A CRIAR O EXECUTAVEL DO SLAYER DOWNLOADER
echo ===================================================
echo.

echo 1. Instalando dependencias...
python -m pip install pypiwin32 pyinstaller Pillow

echo.
echo 2. A verificar FFmpeg...

if exist "ffmpeg.exe" (
    echo    FFmpeg encontrado localmente.
) else (
    echo    FFmpeg nao encontrado. A descarregar automaticamente...
    echo    Isto pode demorar um pouco...
    
    REM Descarregar FFmpeg do GitHub (versao essentials, mais leve)
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg-download.zip'"
    
    if not exist "ffmpeg-download.zip" (
        echo    ERRO: Nao foi possivel descarregar o FFmpeg.
        echo    Descarrega manualmente de https://www.gyan.dev/ffmpeg/builds/
        echo    e coloca ffmpeg.exe na pasta raiz do projeto.
        pause
        exit /b 1
    )
    
    echo    A extrair FFmpeg...
    powershell -Command "Expand-Archive -Path 'ffmpeg-download.zip' -DestinationPath 'ffmpeg-temp' -Force"
    
    REM Copiar o executavel da subpasta bin para a raiz
    for /d %%D in (ffmpeg-temp\ffmpeg-*) do (
        if exist "%%D\bin\ffmpeg.exe" (
            copy /Y "%%D\bin\ffmpeg.exe" "ffmpeg.exe" >nul
            echo    FFmpeg extraido com sucesso!
        )
    )
    
    REM Limpar ficheiros temporarios
    del /Q "ffmpeg-download.zip" 2>nul
    rd /S /Q "ffmpeg-temp" 2>nul
    
    if not exist "ffmpeg.exe" (
        echo    ERRO: Nao foi possivel extrair o FFmpeg.
        echo    Descarrega manualmente de https://www.gyan.dev/ffmpeg/builds/
        pause
        exit /b 1
    )
)

echo.
echo 3. A compilar o downloader.py num EXE (isso pode demorar uns minutos)...
python -m PyInstaller --noconfirm --onefile --windowed --name "SlayerDownloader" --icon "assets\icon.ico" --add-data "assets;assets" "downloader.py"

echo.
echo 4. A criar pasta final "SlayerDownloader"...
if exist "SlayerDownloader" rd /S /Q "SlayerDownloader"
mkdir "SlayerDownloader"
copy /Y "dist\SlayerDownloader.exe" "SlayerDownloader\SlayerDownloader.exe" >nul
copy /Y "ffmpeg.exe" "SlayerDownloader\ffmpeg.exe" >nul

echo.
echo ===================================================
echo CONCLUIDO! 
echo.
echo A pasta "SlayerDownloader\" contem tudo pronto:
echo   - SlayerDownloader.exe
echo   - ffmpeg.exe
echo.
echo Podes comprimir esta pasta num .rar para distribuir!
echo ===================================================
pause
