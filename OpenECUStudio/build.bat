@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  OpenECU Studio - Compilation Windows (PyInstaller)
REM  PREREQUIS : Python 3.11 **32 bits (x86)** obligatoire
REM  (la DLL Scanmatik smj2534.dll est 32 bits ; voir README.md)
REM ============================================================

cd /d "%~dp0"

python -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 else 1)"
if errorlevel 1 (
    echo [ERREUR] Python 32 bits (x86) requis. Python actuel :
    python -c "import struct,sys; print('  ', sys.version); print('   pointeurs =', struct.calcsize('P')*8, 'bits')"
    echo Installez Python 3.11 32 bits et relancez ce script depuis cet environnement.
    exit /b 1
)

echo [1/3] Installation des dependances...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [2/3] Nettoyage des builds precedents...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/3] Compilation PyInstaller...
python -m PyInstaller --clean --noconfirm build_windows.spec
if errorlevel 1 exit /b 1

echo.
echo ============================================================
echo  Build termine : dist\OpenECU_Studio.exe
echo  Copiez le dossier 'definitions\' a cote de l'exe si besoin.
echo ============================================================
endlocal
