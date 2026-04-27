@echo off
echo ===================================================
echo     A CRIAR O EXECUTAVEL DO SLAYER DOWNLOADER
echo ===================================================
echo.

echo 1. Instalando dependencias...
python -m pip install pypiwin32 pyinstaller

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
    
    REM Copiar os executaveis da subpasta bin para a raiz
    for /d %%D in (ffmpeg-temp\ffmpeg-*) do (
        if exist "%%D\bin\ffmpeg.exe" (
            copy /Y "%%D\bin\ffmpeg.exe" "ffmpeg.exe" >nul
            copy /Y "%%D\bin\ffprobe.exe" "ffprobe.exe" >nul
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
echo 4. A copiar FFmpeg para a pasta dist...
copy /Y "ffmpeg.exe" "dist\ffmpeg.exe" >nul
echo    FFmpeg copiado para dist\

echo.
echo ===================================================
echo CONCLUIDO! 
echo O teu EXE esta agora disponivel dentro da pasta "dist\"
echo Basta abrir o SlayerDownloader.exe e usar!
echo ===================================================
pause
