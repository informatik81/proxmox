@echo off
setlocal enabledelayedexpansion
title OpenECU Studio - Installation et compilation automatique
cd /d "%~dp0"

set "LOG=%~dp0installation_opencu.log"
echo [%date% %time%] Installation OpenECU Studio >> "%LOG%"

echo ============================================================
echo  OpenECU Studio - installation et compilation automatiques
echo  (Python 3.10 32 bits + PySide2 + PyInstaller)
echo ============================================================
echo.
echo  IMPORTANT : laissez cette fenetre ouverte jusqu'au message final.
echo  Chaque etape affiche son numero ; en cas d'erreur, la fenetre
echo  reste ouverte et le message d'erreur reste visible.
echo.

REM ============================================================
REM  ETAPE 1 : trouver un Python 3.10 32 bits deja installe
REM ============================================================
echo [ETAPE 1/6] Recherche d'un Python 3.10 32 bits (x86)...
set "PYCMD="
call :find_python310_32

REM ============================================================
REM  ETAPE 2 : installer Python 3.10.11 32 bits si absent
REM ============================================================
if defined PYCMD (
    echo           Python 3.10 32 bits deja installe, etape ignoree.
    goto :goto_python
)
echo [ETAPE 2/6] Python 3.10 32 bits introuvable : telechargement (environ 26 Mo)...
echo [%date% %time%] Telechargement Python 3.10.11 x86 >> "%LOG%"
set "PYINST=%TEMP%\python-3.10.11.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11.exe' -OutFile '%PYINST%' -UseBasicParsing; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 2/6] Telechargement impossible ^(connexion Internet, proxy ou antivirus^).
    echo   1. Verifiez votre connexion Internet.
    echo   2. Ou installez manuellement Python 3.10.11 32 bits :
    echo      https://www.python.org/downloads/release/python-31011/
    echo      ^(fichier "Windows installer (32-bit)"^)
    echo   3. Puis relancez ce fichier.
    echo [%date% %time%] ERREUR telechargement >> "%LOG%"
    pause
    exit /b 1
)
echo           Installation silencieuse de Python 3.10.11 32 bits (2-3 minutes, sans fenetre)...
"%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 2/6] Echec de l'installation de Python.
    echo   Lancez manuellement le fichier : %PYINST%
    echo   Cochez "Add Python to PATH" et laissez l'option 32 bits par defaut.
    echo [%date% %time%] ERREUR installation Python >> "%LOG%"
    pause
    exit /b 1
)
call :find_python310_32
if not defined PYCMD (
    echo.
    echo [ERREUR ETAPE 2/6] Python 3.10 32 bits non detecte apres installation.
    echo   Fermez TOUTES les fenetres, rouvrez le dossier et relancez ce fichier.
    echo [%date% %time%] ERREUR detection Python >> "%LOG%"
    pause
    exit /b 1
)

:goto_python
echo           Python 32 bits detecte : %PYCMD%
%PYCMD% -c "import sys; print('           ->', sys.version.split()[0], '(x86)')" >> "%LOG%" 2>&1

REM ============================================================
REM  ETAPE 3 : environnement virtuel .venv32
REM ============================================================
echo [ETAPE 3/6] Creation de l'environnement virtuel .venv32...
if not exist ".venv32" %PYCMD% -m venv .venv32
set "VPY=%~dp0.venv32\Scripts\python.exe"
if not exist "%VPY%" (
    echo.
    echo [ERREUR ETAPE 3/6] Environnement virtuel non cree : %VPY%
    echo   Supprimez le dossier .venv32 puis relancez ce fichier.
    echo [%date% %time%] ERREUR venv >> "%LOG%"
    pause
    exit /b 1
)
"%VPY%" -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 else 1)"
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 3/6] L'environnement .venv32 n'est PAS en 32 bits.
    echo   Supprimez le dossier .venv32 puis relancez ce fichier.
    echo [%date% %time%] ERREUR venv 64 bits >> "%LOG%"
    pause
    exit /b 1
)
echo           Environnement .venv32 pret (Python 32 bits verifie).

REM ============================================================
REM  ETAPE 4 : dependances (PySide2 + PyInstaller) - affichage complet
REM ============================================================
echo [ETAPE 4/6] Installation des dependances PySide2 et PyInstaller (1-2 minutes)...
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 4/6] Echec de mise a jour de pip (connexion Internet ?).
    echo [%date% %time%] ERREUR pip upgrade >> "%LOG%"
    pause
    exit /b 1
)
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 4/6] Echec de l'installation des dependances.
    echo   Causes possibles : antivirus, proxy d'entreprise, connexion coupee.
    echo [%date% %time%] ERREUR pip install >> "%LOG%"
    pause
    exit /b 1
)
"%VPY%" -c "import PySide2; print('PySide2', PySide2.__version__)" >> "%LOG%" 2>&1
"%VPY%" -c "import PySide2; assert PySide2.__version__" 2>nul
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 4/6] PySide2 introuvable dans .venv32 (installation incomplete).
    echo [%date% %time%] ERREUR import PySide2 >> "%LOG%"
    pause
    exit /b 1
)

REM ============================================================
REM  ETAPE 5 : compilation de l'executable (PyInstaller)
REM ============================================================
echo [ETAPE 5/6] Compilation de OpenECU_Studio.exe (2-5 minutes, patientez)...
echo [%date% %time%] Debut PyInstaller >> "%LOG%"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
"%VPY%" -m PyInstaller --clean --noconfirm build_windows.spec
if errorlevel 1 (
    echo.
    echo [ERREUR ETAPE 5/6] Echec de la compilation PyInstaller.
    echo   Relancez ce fichier ; si l'echec persiste, envoyez le texte
    echo   affiche ci-dessus au support.
    echo [%date% %time%] ERREUR PyInstaller >> "%LOG%"
    pause
    exit /b 1
)
if not exist "dist\OpenECU_Studio.exe" (
    echo.
    echo [ERREUR ETAPE 5/6] dist\OpenECU_Studio.exe absent apres compilation.
    echo [%date% %time%] ERREUR exe absent >> "%LOG%"
    pause
    exit /b 1
)

REM ============================================================
REM  ETAPE 6 : definitions a cote de l'exe + lancement
REM ============================================================
if not exist "dist\definitions" xcopy /e /i /y "definitions" "dist\definitions" >nul
echo [%date% %time%] SUCCES - dist\OpenECU_Studio.exe >> "%LOG%"
echo [ETAPE 6/6] Termine : dist\OpenECU_Studio.exe
echo.
echo ============================================================
echo  COMPILATION REUSSIE
echo  L'application se trouve ici : %~dp0dist\OpenECU_Studio.exe
echo.
echo  Sans SM2 Pro branchee : dans l'onglet Diagnostic, choisir
echo  l'interface "Simulation / Mock J2534" puis "Se connecter".
echo ============================================================
start "" "dist\OpenECU_Studio.exe"
timeout /t 8 >nul
exit /b 0

REM ------------------------------------------------------------
REM  Recherche d'un Python 3.10 32 bits
REM  (PySide2 32 bits requiert Python 3.5 a 3.10 ; 3.11 refuse)
REM ------------------------------------------------------------
:find_python310_32
set "PYCMD="
for %%P in ("C:\Windows\py.exe" "%LocalAppData%\Programs\Python\Launcher\py.exe") do (
    if exist "%%~P" (
        "%%~P" -3.10-32 -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 and sys.version_info[:2]==(3,10) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PYCMD=%%~P -3.10-32"
            goto :eof
        )
    )
)
for %%P in ("%LocalAppData%\Programs\Python\Python310-32\python.exe" "%ProgramFiles%\Python310-32\python.exe") do (
    if exist "%%~P" (
        "%%~P" -c "import struct,sys; sys.exit(0 if struct.calcsize('P')==4 and sys.version_info[:2]==(3,10) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PYCMD=%%~P"
            goto :eof
        )
    )
)
goto :eof
