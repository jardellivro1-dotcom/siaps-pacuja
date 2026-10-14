@echo off
chcp 65001 >nul
title Painel APS Pacuja
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PORT=8000

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".
  pause
  exit /b 1
)

echo Buscando dados novos no Siaps...
python -m siaps_pacuja update
if errorlevel 1 (
  echo.
  echo Nao foi possivel atualizar agora ^(sem internet?^). Abrindo com os dados ja salvos.
  python -m siaps_pacuja build
)

echo.
echo Abrindo o painel em http://127.0.0.1:%PORT%  ^(feche esta janela para encerrar^)
start "" "http://127.0.0.1:%PORT%"
python -m siaps_pacuja serve --port %PORT%
pause
