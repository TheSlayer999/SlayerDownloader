#!/bin/bash
# Script para compilar o SlayerHub no macOS e gerar um ficheiro .dmg pronto para distribuição

echo "🧹 Limpando builds anteriores..."
rm -rf build dist

echo "🔨 Compilando a aplicação com PyInstaller..."
if [ -f ".venv/bin/pyinstaller" ]; then
    .venv/bin/pyinstaller --noconfirm --noconsole --name "SlayerHub" --icon "assets/icon.ico" downloader.py
else
    pyinstaller --noconfirm --noconsole --name "SlayerHub" --icon "assets/icon.ico" downloader.py
fi

if [ ! -d "dist/SlayerHub.app" ]; then
    echo "❌ Erro: O pacote SlayerHub.app não foi gerado."
    exit 1
fi

echo "🔐 Assinando a aplicação (Ad-hoc) para evitar erros do Gatekeeper..."
codesign --force --deep -s - dist/SlayerHub.app

echo "📦 Criando o ficheiro DMG..."
hdiutil create -volname "SlayerHub" -srcfolder dist/SlayerHub.app -ov -format UDZO dist/SlayerHubMac.dmg

echo "✅ Concluído! O ficheiro SlayerHubMac.dmg está disponível na pasta 'dist'."
