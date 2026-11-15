@echo off
cd /d "%~dp0"
title Forja - Wakfu Damage Meter

:: Extrai automaticamente a versao (APP_VERSION) de dentro do arquivo Python
for /f "tokens=2 delims==" %%I in ('findstr /B "APP_VERSION" "Wakfu Damage Meter.py"') do set "RAW_VER=%%~I"
set "RAW_VER=%RAW_VER: =%"
set "RAW_VER=%RAW_VER:"=%"
set "VERSAO=v%RAW_VER%"

echo ===================================================
echo   FORJA - WAKFU DAMAGE METER (%VERSAO%)
echo ===================================================
echo.

echo [1/3] Forjando o aplicativo executavel...
python -m PyInstaller --noconfirm --clean --onedir --windowed --collect-submodules openpyxl --add-data "icone.ico;." --icon="icone.ico" "Wakfu Damage Meter.py"

echo.
echo [2/3] Copiando avatares e icone para o diretorio final...
if exist "avatares" (
    xcopy /E /I /Y "avatares\*" "dist\Wakfu Damage Meter\avatares\" > NUL
)
if exist "icone.ico" (
    copy /Y "icone.ico" "dist\Wakfu Damage Meter\" > NUL
)

echo.
echo [3/3] Compactando a versao final (Wakfu Damage Meter_%VERSAO%.zip)...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Wakfu Damage Meter' -DestinationPath 'dist\Wakfu Damage Meter_%VERSAO%.zip' -Force"

echo.
echo Forja concluida com sucesso! O arquivo "Wakfu Damage Meter_%VERSAO%.zip" esta pronto na pasta dist.
pause