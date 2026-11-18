# OpenECU Studio

Application desktop Windows 10 en **Python 3.11 (32 bits)** + **PySide6** pour :

1. **Diagnostic temps réel** via une interface matérielle **Scanmatik 2 Pro (SM2 Pro)** — API standard **SAE J2534-1** (`smj2534.dll`), couche **ISO-TP (ISO 15765-2)** et **UDS (ISO 14229)**.
2. **Édition offline de fichiers binaires ECU** (`.bin` / `.ori`) : détection de famille (Bosch EDC17, Siemens/Continental SID807/PCR2.1, Delphi DCM6.2, Marelli MJ8/MJ9), **DTC Remover**, solutions EGR/DPF/AdBlue/Swirl par signatures hexadécimales pilotées par des définitions JSON, comparateur hexadécimal et surveillance des checksums.

> ⚠️ **AVERTISSEMENT LÉGAL ET SÉCURITÉ**
> La modification des systèmes antipollution (EGR, DPF/FAP, SCR/AdBlue) et la désactivation de codes défauts sur un véhicule **circulant sur voie publique est interdite** dans la plupart des pays (UE : règlement (UE) 2018/858, France : code de la route art. R318-4, contrôle technique...). OpenECU Studio est fourni à des fins **d'ingénierie, de diagnostic, de recherche et d'usage piste/circuit/racing** uniquement. L'utilisateur est seul responsable de l'usage qu'il en fait et de la conformité à la législation de son pays. Toute écriture dans un ECU réel se fait **à vos risques et périls** : un flash mal préparé (checksum non corrigé, mauvais fichier) peut rendre le calculateur inutilisable (bricked).

---

## Sommaire

1. [Prérequis](#1-prérequis)
2. [Installation de Python 3.11 32 bits (OBLIGATOIRE)](#2-installation-de-python-311-32-bits-obligatoire)
3. [Installation des pilotes Scanmatik SM2 Pro](#3-installation-des-pilotes-scanmatik-sm2-pro)
4. [Installation du projet et lancement](#4-installation-du-projet-et-lancement)
5. [Utilisation](#5-utilisation)
6. [Compilation de l'exécutable (.exe)](#6-compilation-de-lexécutable-exe)
7. [Format des définitions JSON](#7-format-des-définitions-json)
8. [Architecture du code](#8-architecture-du-code)
9. [Dépannage](#9-dépannage)

---

## 1. Prérequis

| Élément | Détail |
|---|---|
| OS | Windows 10 / 11 (x86 ou x64 — voir section 2) |
| Python | **3.11 32 bits (x86)** — obligatoire pour le J2534 matériel |
| Interface | Scanmatik 2 Pro (SM2 Pro) + pilotes PassThru 04.04 installés |
| Véhicule | OBD2 (CAN 500 kbps, broches 6/14 ; VBatt broche 16) |

**Pourquoi 32 bits ?** La DLL officielle Scanmatik `smj2534.dll` est une bibliothèque **32 bits**, enregistrée sous :

```
HKLM\SOFTWARE\WOW6432Node\PassThruSupport.04.04
```

Un processus 64 bits ne peut pas charger une DLL 32 bits : `ctypes.WinDLL` lèverait
`OSError: [WinError 193] %1 n'est pas une application Win32 valide`.
Toute la chaîne (Python + PyInstaller + exe) doit donc être **x86**.

## 2. Installation de Python 3.11 32 bits (OBLIGATOIRE)

1. Téléchargez **Python 3.11.x « Windows installer (32-bit) »** depuis <https://www.python.org/downloads/windows/> (fichier `python-3.11.x.exe` dont le nom contient *32-bit*).
2. Lancez l'installeur et **cochez** :
   - `Add python.exe to PATH`
   - `Install for all users`
3. Vérifiez l'architecture dans un **nouveau** terminal :

```bat
python -c "import struct,sys; print(sys.version); print('bits =', struct.calcsize('P')*8)"
:: doit afficher : bits = 32
```

Si vous gardez aussi un Python 64 bits, utilisez le lanceur py :
`py -3.11-32` ou le chemin complet `C:\Users\<vous>\AppData\Local\Programs\Python\Python311-32\python.exe`.

## 3. Installation des pilotes Scanmatik SM2 Pro

1. Branchez la SM2 Pro en USB (sans la connecter au véhicule).
2. Installez le paquet de pilotes Scanmatik (CD fourni ou site officiel Scanmatik) qui enregistre
   `smj2534.dll` dans le registre sous `HKLM\SOFTWARE\WOW6432Node\PassThruSupport.04.04`.
3. Vérifiez la présence de la clé (Win+R → `regedit`) :

```
HKLM\SOFTWARE\WOW6432Node\PassThruSupport.04.04\SM2 USB
   FunctionType = C:\...\smj2534.dll
```

OpenECU Studio énumère automatiquement toutes les interfaces PassThru 04.04 et place
les entrées « SM2 » / « Scanmatik » en tête de liste.

## 4. Installation du projet et lancement

### Option rapide — un seul fichier à exécuter

Double-cliquez sur **`INSTALLER_OPENECU.bat`** (dans le dossier `OpenECUStudio`). Il fait tout, dans l'ordre :

1. détecte un Python 32 bits ; s'il n'existe pas, **télécharge et installe automatiquement Python 3.11.9 (32 bits)** depuis python.org ;
2. crée un environnement virtuel `.venv32` et installe les dépendances (PySide6, PyInstaller) ;
3. compile `dist\OpenECU_Studio.exe` (PyInstaller) et copie `definitions/` à côté de l'exe ;
4. lance l'application.

En cas d'erreur, le message affiché indique l'étape exacte à corriger.

### Option manuelle

```bat
cd OpenECUStudio
python -m pip install -r requirements.txt
python main.py
```

Sans SM2 Pro branchée, choisissez dans l'onglet Diagnostic l'entrée
**« Simulation / Mock J2534 (sans matériel) »** : un EDC17C10 fictif répond aux
requêtes UDS (VIN, N° HW/SW, DTC P0401/P2002/P2463/P2263, effacement) pour tester
toute la chaîne sans véhicule.

## 5. Utilisation

### Thèmes sombre et clair (v1.2.0)

L'interface propose **deux thèmes complets** : **sombre** (par défaut, style industriel)
et **clair**. Le changement se fait depuis le menu **Affichage → Thème sombre / Thème clair**
au sommet de la fenêtre : il est **immédiat**, mémorisé dans `settings.json`
(l'app rouvre dans le dernier thème utilisé) et **tous les libellés restent lisibles**
dans les deux modes — les couleurs dynamiques (VBatt, statuts, checksums, diff) suivent
automatiquement le thème actif.


### Onglet 1 — Diagnostic & SM2 Pro (J2534)
- **Interface** : sélection + connexion (ISO 15765, 500 kbps, 0x7E0/0x7E8).
- **Configuration CAN** : vitesse (125 k / 250 k / 500 k / 1 M bauds), **ID requête (TX)** et **ID réponse (RX)** configurables (ex. 0x7E4/0x7EC sur certains véhicules) ; les réglages sont **mémorisés** dans `settings.json` (interface, vitesse, IDs, dernier dossier).
- **Tester Present automatique (2 s)** : case à cocher qui maintient la session de diagnostic active en envoyant `3E 00` toutes les 2 secondes (les échanges UDS sont sérialisés, aucun entrelacement possible).
- **VBatt** : tension batterie lue en temps réel (1 Hz) via `PassThruIoctl(READ_VBATT)`.
- **Identifier ECU (UDS)** : session étendue `10 03` puis `22 F190` (VIN), `22 F191` (N° HW), `22 F195` (N° SW).
- **Lire les DTC** : `19 02 FF` (reportDTCByStatusMask).
- **Effacer les DTC** (`14 FF FF FF`) : ⚠️ opération irréversible sur la mémoire de l'ECU — une **confirmation explicite** est demandée avant exécution.
- **Console** : toutes les trames CAN/UDS brutes (TX/RX) horodatées.
- **Fermeture propre** : à la sortie de l'application, matériel déconnecté, timers arrêtés, réglages sauvegardés.

### Onglet 2 — Éditeur ECU & Patcher (Offline)
1. **Charger un fichier ECU** : une sauvegarde horodatée `.bak` est créée **immédiatement** (ex. `dump_20250101_120000.bak`) avant toute modification.
2. La **fiche d'identité** (famille détectée, entropie, n° de pièce, SHA-256) s'affiche ; la définition la plus compatible est sélectionnée automatiquement.
3. Cochez les **solutions** (EGR Off, DPF Off, AdBlue Off, Swirl Flaps Off) définies dans le JSON puis **Appliquer** — une **fenêtre de mise en garde** (cadre légal + risque checksum) s'affiche avant toute écriture.
4. **DTC Remover** : cliquez *Scanner* — chaque code (ex. `P0401`, `P2002`, `P2463`) est listé avec son **offset hexadécimal** ; utilisez la barre de recherche, sélectionnez les lignes puis **Désactiver les DTC sélectionnés** (octet switch mis à `0x00`, également précédé d'une confirmation).
5. **Sauvegarder le calculateur (copie)** : enregistre une copie du fichier **tel que chargé** (non modifié) à l'emplacement de votre choix, en plus de la sauvegarde `.bak` horodatée automatique.
6. La **fermeture de l'application** vous avertit si des modifications n'ont pas été exportées.

### Sécurité des opérations (récapitulatif)

| Action | Protection intégrée |
|---|---|
| Chargement d'un dump | Sauvegarde `.bak` horodatée automatique, avant toute modification |
| Solutions EGR/DPF/AdBlue/Papilles | Confirmation avec rappel légal (UE 2018/858, art. R318-4) |
| Désactivation de DTC | Confirmation avec rappel des risques (panne masquée, contrôle technique) |
| Remplacement du VIN | Confirmation avec cadre légal (art. 441-1 du code pénal) et rappel d'appairage immo/BSI |
| Effacement des DTC dans l'ECU (UDS) | Confirmation — action irréversible sur la mémoire ECU |
| Export du `.bin` patché | Confirmation si checksums en écart + avertissement « risque de calculateur inutilisable » |
| Annulation de session | Confirmation, sauvegardes `.bak` conservées |
| Fermeture de l'application | Avertissement si modifications non exportées |

### Réemploi d'un calculateur d'occasion (au lieu de le jeter)

L'application couvre la partie **fichier** du réemploi d'un ECU de récupération :

1. **Identifier le donneur** : onglet 1, lecture UDS du VIN et des n° HW/SW — à comparer avec les besoins du véhicule cible (compatibilité référence + version logicielle).
2. **Dumper le calculateur donneur** (outil de lecture dédié) et le charger dans l'onglet 2 — une sauvegarde `.bak` est créée à l'instant.
3. **Préparer le fichier** :
   - **VIN** : le groupe « Réemploi — VIN » détecte automatiquement **toutes** les occurrences du VIN dans le dump (flash + zones d'appairage), valide le caractère de contrôle ISO 3779 (informationnel — les VIN européens ne l'utilisent pas tous) et le remplace de façon synchronisée dans tout le dump ;
   - **DTC / solutions** : via les définitions JSON (onglet 4) selon la famille.
4. **Écrire le fichier préparé** dans le calculateur avec un outil de flash (SM2 Pro mode flash, MPPS, KESS...).
5. **Appairer au véhicule** : le VIN est aussi stocké dans les autres calculateurs (immo/BSI/UCH) et le codage d'appairage se fait avec un outil de diagnostic compatible constructeur — sans cette étape, le moteur ne démarrera pas.

⚠️ Usage légitime = **réparation / réutilisation** (remplacer un ECU défectueux par un équivalent d'occasion). La modification du VIN dans un but de dissimulation d'identité de véhicule est un délit (faux et usage de faux).

### Onglet 3 — Comparateur Hexadécimal
Table `Offset | D'origine | Modifié` de tous les octets changés, filtrable, avec export final du `.bin` patché (l'export sauvegarde aussi un fichier existant en `.bak` et affiche l'**état des checksums**).

### Onglet 4 — Gestionnaire de Définitions
Éditeur JSON intégré avec validation : créez/importez de nouvelles définitions pour d'autres calculateurs **sans recompiler** (les fichiers vivent dans `definitions/` à côté de l'exe).

## 6. Compilation de l'exécutable (.exe)

Depuis l'environnement **Python 3.11 32 bits** :

```bat
build.bat
```

Le script vérifie l'architecture (il refuse un Python 64 bits), installe les dépendances puis lance PyInstaller avec `build_windows.spec` (mode `--onefile --windowed`, dossier `definitions/` embarqué) :

```
dist\OpenECU_Studio.exe
```

Pour un build manuel : `python -m PyInstaller --clean --noconfirm build_windows.spec`.
Copiez (ou laissez l'utilisateur éditer) le dossier `definitions/` à côté de l'exe pour ajouter des définitions après compilation.

## 7. Format des définitions JSON

```jsonc
{
  "schema_version": 1,
  "definition_id": "mon_calculateur",
  "name": "Nom affiché",
  "manufacturer": "Bosch",
  "ecu_families": ["EDC17C10"],
  "match": {
    "id_patterns": ["EDC17"],       // chaînes ASCII cherchées dans le dump
    "min_size": 1048576,             // plage de tailles acceptées (octets)
    "max_size": 8388608
  },
  "checksum": {
    "notes": "Avertissement affiché avant export",
    "regions": [                     // algorithmes disponibles : crc32, sum16, sum32, twos_complement32
      {"algorithm": "crc32", "start": 0, "length": 2097152, "storage_offset": null, "endianness": "little"}
    ]
  },
  "solutions": [
    {
      "id": "egr_off",
      "label": "EGR Off",
      "category": "antipollution",
      "description": "...",
      "patches": [
        {
          "name": "Nom du patch",
          "find":    "48 8B ?? ?? 00 00 74 ??",   // ?? = wildcard (octet quelconque)
          "replace": "48 8B ?? ?? 00 00 EB ??",   // ?? = octet d'origine conservé
          "description": "JZ -> JMP"
        }
      ]
    }
  ],
  "dtc_tables": [
    {
      "name": "Table DTC principale",
      "entry_size": 4,          // octets par entrée DTC
      "code_offset": 0,         // offset du code (2 octets) dans l'entrée
      "switch_offset": 3,       // offset de l'octet d'activation (mis à 0x00)
      "byte_order": "big",      // encodage du code DTC (SAE J2012 : P0401 = 04 01)
      "locator": null,          // motif hexa optionnel localisant la table (sinon scan brut)
      "min_entries": 8          // densité minimale pour valider une table
    }
  ],
  "notes": ""
}
```

Le **scan brut** (sans localisateur) détecte automatiquement les séquences d'au moins
8 entrées DTC consécutives valides (format SAE J2012 : nibble système 0-3 → P/C/B/U).

## 8. Architecture du code

```
OpenECUStudio/
├── main.py                        # Point d'entrée : logging, excepthook, QApplication
├── core/
│   ├── j2534_driver.py            # winreg + ctypes WinDLL (ABI Win32), PASSTHRU_MSG/SCONFIG,
│   │                              #   ISO-TP (ISO 15765-2), UDS (ISO 14229), Mock J2534
│   ├── ecu_analyzer.py            # Détection de famille, entropie, chaînes, motifs ?? wildcards
│   ├── patch_engine.py            # Définitions JSON, patches, DTC Remover, .bak, diffs, export
│   └── checksum.py                # CRC32 / somme 16-32 bits / complément à 2 (extensible)
├── ui/
│   ├── theme.py                   # Dark Mode industriel (Fusion + QSS)
│   ├── workers.py                 # QThread générique
│   ├── main_window.py             # Assemblage des onglets
│   ├── tab_diagnostics.py         # Onglet 1 : J2534, VBatt, UDS, DTC, console
│   ├── tab_patcher.py             # Onglet 2 : dump, solutions, DTC Remover
│   ├── tab_diff.py                # Onglet 3 : comparateur hexadécimal
│   └── tab_definitions.py         # Onglet 4 : gestionnaire de définitions
├── definitions/
│   ├── bosch_edc17_generic_dtc.json
│   └── psa_sid807_egr_dpf.json
├── build_windows.spec             # PyInstaller (onefile, windowed)
├── build.bat                      # Build automatisé (vérifie Python 32 bits)
├── requirements.txt
└── logs/                          # Journaux horodatés
```

## 9. Dépannage

| Symptôme | Cause / solution |
|---|---|
| `OSError: [WinError 193] %1 n'est pas une application Win32 valide` | Python **64 bits** : réinstallez/relancez avec Python 3.11 **32 bits** (section 2). |
| Aucune interface dans la liste | Pilotes Scanmatik non installés, ou clé absente de `HKLM\SOFTWARE\WOW6432Node\PassThruSupport.04.04` — réinstallez les pilotes et cliquez *Rafraîchir*. |
| `ERR_DEVICE_NOT_CONNECTED` | Boîtier USB débranché ou occupé par une autre application ; déconnectez, rebranchez, *Rafraîchir*. |
| `UdsTimeoutError` | Contact allumé requis, mauvais IDs (essayez 0x7E4/0x7EC sur certains véhicules), ou ECU sur un autre bus. |
| DTC introuvable dans le dump | Le scan brut exige ≥ 8 entrées consécutives valides ; ajoutez un `locator` et les offsets réels dans la définition JSON. |
| ECU refuse le fichier après flash | **Checksum non corrigé** : utilisez un outil de checksum dédié pour la famille (cf. avertissement dans les définitions). |
| L'exe ne démarre pas | Lancez-le depuis un terminal pour lire l'erreur ; vérifiez que `definitions/` est présent à côté de l'exe et consultez `logs/`. |

---

## 10. Tests et intégration continue (v1.1.0)

La logique métier (checksums, analyseur, moteur de patch, couche J2534/UDS, réglages) est couverte par une suite de tests automatisée :

```
python -m pip install pytest
python -m pytest tests -q
```

Les tests tournent **sans aucun matériel** (mode simulation J2534 intégré) et sans Windows
(les structures ABI Win32 ne sont vérifiées que sous Windows). L'interface Qt n'est pas
testée (rendu graphique), mais les imports d'UI sont validés à chaque build.

Chaque push ou pull request modifiant `OpenECUStudio/**` déclenche le workflow
GitHub Actions « OpenECU Studio tests » (pyflakes + pytest sur Python 3.11) : cf.
`.github/workflows/opencu-tests.yml`.

L'historique complet des versions est documenté dans `CHANGELOG.md`.
