@echo off
setlocal enabledelayedexpansion
title OpenECU Studio - Installation et compilation automatique
cd /d "%~dp0"

echo ============================================================
echo  OpenECU Studio - installation et compilation automatiques
echo ============================================================
echo.

REM ============================================================
REM  1) Trouver (ou installer) un Python 3.11 32 bits
REM     Obligatoire : la DLL Scanmatik smj2534.dll est 32 bits.
REM ============================================================
set "PYEXE="
call :find_python32
if defined PYEXE goto :got_python

echo [1/4] Python 32 bits introuvable : telechargement de Python 3.11.9 (32 bits)...
set "PYINST=%TEMP%\python-3.11.9.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe' -OutFile '%PYINST%' -UseBasicParsing; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo [ERREUR] Telechargement impossible ^(connexion ou proxy^).
    echo          Installez manuellement Python 3.11 32 bits depuis :
    echo          https://www.python.org/downloads/windows/
    echo          Puis relancez ce fichier.
    pause
    exit /b 1
)
echo       Installation silencieuse de Python 3.11 32 bits (2-3 minutes)...
"%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation. Lancez manuellement : %PYINST%
    pause
    exit /b 1
)
call :find_python32
if not defined PYEXE (
    echo [ERREUR] Python 32 bits non detecte apres installation.
    echo          Fermez cette fenetre, rouvrez-la et relancez ce fichier.
    pause
    exit /b 1
)

:got_python
echo [1/4] Python 32 bits detecte : %PYEXE%
%PYEXE% -c "import sys; print('       ', sys.version.split()[0], '(x86)')"

REM ============================================================
REM  2) Environnement virtuel + dependances
REM ============================================================
echo [2/4] Environnement virtuel et dependances (PySide6, PyInstaller)...
if not exist ".venv32" %PYEXE% -m venv .venv32
set "VPY=%~dp0.venv32\Scripts\python.exe"
if not exist "%VPY%" (
    echo [ERREUR] Environnement virtuel non cree : %VPY%
    pause
    exit /b 1
)
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances (connexion Internet ?).
    pause
    exit /b 1
)

REM ============================================================
REM  3) Compilation de l'executable (PyInstaller)
REM ============================================================
echo [3/4] Compilation de OpenECU_Studio.exe (2-5 minutes, patientez)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
"%VPY%" -m PyInstaller --clean --noconfirm build_windows.spec
if errorlevel 1 (
    echo [ERREUR] Echec de la compilation. Relancez ce fichier ou verifiez les messages ci-dessus.
    pause
    exit /b 1
)
if not exist "dist\OpenECU_Studio.exe" (
    echo [ERREUR] dist\OpenECU_Studio.exe absent apres compilation.
    pause
    exit /b 1
)

REM ============================================================
REM  4) Definitions a cote de l'exe + lancement
REM ============================================================
if not exist "dist\definitions" xcopy /e /i /y "definitions" "dist\definitions" >nul
echo [4/4] Compilation terminee : dist\OpenECU_Studio.exe
echo.
echo ============================================================
echo  Lancement d'OpenECU Studio...
echo  Sans SM2 Pro : choisir "Simulation / Mock J2534" dans l'onglet
echo  Diagnostic, puis "Se connecter".
echo ============================================================
start "" "dist\OpenECU_Studio.exe"
timeout /t 8 >nul
exit /b 0

REM ------------------------------------------------------------
REM  Recherche d'un interpreteur Python 32 bits
REM ------------------------------------------------------------
:find_python32
set "PYEXE="
py -3.11-32 -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 else 1)" >nul 2>&1 && set "PYEXE=py -3.11-32" && goto :eof
python -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 else 1)" >nul 2>&1 && set "PYEXE=python" && goto :eof
for %%P in ("%LocalAppData%\Programs\Python\Python311-32\python.exe" "%ProgramFiles%\Python311-32\python.exe" "%LocalAppData%\Programs\Python\Python311\python.exe" "%ProgramFiles%\Python311\python.exe") do (
    if exist "%%~P" (
        "%%~P" -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 else 1)" >nul 2>&1 && set "PYEXE=%%~P" && goto :eof
    )
)
goto :eof
