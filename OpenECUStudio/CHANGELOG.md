# Changelog — OpenECU Studio

Toutes les évolutions notables du projet sont documentées ici (format « Keep a Changelog »).

## [1.2.1] — Correctif installateur : bascule PySide2 (Qt5)

### Corrigé
- **Installation bloquée sans `dist/`** : Qt 6 (PySide6) n'est distribué que pour
  Windows 64 bits — aucun wheel « win32 » n'existe, le `pip install` échouait donc
  systématiquement dans l'environnement Python 32 bits et la compilation n'était
  jamais lancée.
- L'application utilise désormais **PySide2 5.15.2.1 (Qt 5)**, le seul bindings Qt
  avec un wheel 32 bits officiel, compatible **Python 3.10 32 bits**.

### Modifié
- `INSTALLER_OPENECU.bat` réécrit : cible **Python 3.10.11 (32 bits)**, 6 étapes
  numérotées affichées, journal `installation_opencu.log`, vérification du 32 bits
  de l'environnement, import PySide2 contrôlé, `pause` bloquante sur chaque erreur
  avec message explicite.
- Haute densité d'affichage gérée (écrans Windows 125/150 %) sous Qt 5.
- `requirements.txt`, `build.bat`, `README.md` mis à jour en conséquence.

## [1.2.0] — Interface hyper moderne, thème sombre et clair

### Ajouts
- **Thème clair** en plus du thème sombre : palettes complètes (fond, panneaux,
  boutons, tableaux, menus, info-bulles, barres de défilement) avec contraste
  vérifié pour que **tous les textes restent bien lisibles** dans les deux modes.
- **Bascule instantanée** via le menu **Affichage → Thème sombre / Thème clair**,
  avec coche sur le thème actif et message de confirmation dans la barre d'état.
- **Préférence mémorisée** dans `settings.json` : l'application rouvre dans le
  dernier thème utilisé.
- Réglages enrichis (nouvelle clé `theme`, valeur par défaut `dark`).

### Améliorations
- Feuille de style entièrement régénérée depuis la palette (`ThemeColors`) :
  aucun codé en dur, plus de couleurs « texte vert sur fond blanc » illisibles.
- Onglets modernisés (soulignement accentué), coins arrondis, alimentation
  cohérente des états survol/appui/désactivé, menus et info-bulles stylés.
- Les couleurs dynamiques (valeur VBatt, statuts, badge de compatibilité,
  état des checksums, diff accentué) suivent automatiquement le thème actif.

## [1.1.0] — Durcissement production

### Ajouts
- **Suite de tests automatisée** (`tests/`) : 67 tests couvrant checksums, analyseur d'ECU
  (entropie, patterns, VIN, signatures), moteur de patch (sauvegardes, DTC Remover,
  remplacement VIN, export, définitions JSON), couche J2534 (Mock UDS complet, ISO-TP,
  NRC 0x78 « responsePending », réponses négatives) et réglages persistants.
- **Intégration continue** : workflow GitHub Actions exécutant la suite à chaque
  push/PR touchant `OpenECUStudio/`.
- **Réglages persistants** (`settings.json`, écriture atomique) : interface, vitesse CAN,
  ID requête/réponse, Tester Present, dernier dossier utilisé.
- **Onglet Diagnostic** : sélection de la vitesse CAN (125 k–1 M bauds), ID requête (TX)
  et réponse (RX) configurables, **Tester Present automatique (2 s)** maintien de session,
  sauvegarde des réglages à la connexion et à la fermeture.
- **Arrêt propre** : fermeture synchronisée du matériel et des timers à la sortie
  (`closeEvent`), avec avertissement si des modifications ne sont pas exportées.
- **Bouton « Sauvegarder le calculateur (copie) »** : export immédiat d'une copie du
  fichier tel que chargé, en plus de la sauvegarde `.bak` horodatée automatique.
- **Confirmations de sécurité** avant les actions à risque : application des solutions
  antipollution (cadre légal UE 2018/858 / art. R318-4), désactivation de DTC,
  remplacement de VIN (art. 441-1), effacement des DTC dans la mémoire ECU,
  export d'un fichier dont le checksum est en écart.
- Interface 100 % en français.

### Corrections
- **Faux positifs de détection de famille** : les signatures courtes (ex. « MJ9 »,
  3 caractères) se retrouvaient par hasard dans des données aléatoires ; leur influence
  dépend désormais de leur longueur et le seuil de détection est relevé.
- Sérialisation des requêtes UDS par verrou (`RLock`) : le Tester Present périodique ne
  peut plus entremêler ses trames avec celles des autres requêtes.
- Le mode simulation renvoie désormais une réponse négative UDS correcte (NRC 0x31
  « requestOutOfRange ») pour un DID inconnu au lieu d'une réponse positive.

## [1.0.1] — Correctifs de lancement
- Correction d'un plantage à l'ouverture de l'onglet Patcher (`QComboBox` non importé).
- Nettoyage des imports inutilisés (vérifié par pyflakes).

## [1.0.0] — Version initiale
- Onglet Diagnostic & SM2 Pro (J2534) : VBatt temps réel, session étendue, identification
  UDS (VIN / N° matériel / N° logiciel), lecture/effacement des DTC, console CAN brute.
- Onglet Éditeur ECU & Patcher : détection de famille (EDC17, SID807, PCR2.1, DCM6.2,
  Marelli…), solutions par signature `?? / ??` (EGR Off, DPF Off, AdBlue Off,
  Papilles Off), DTC Remover, éditeur de VIN pour réemploi d'un calculateur d'occasion.
- Sauvegarde `.bak` horodatée automatique avant toute modification, restauration,
  annulation de session.
- Onglet Comparateur hexadécimal (offset | d'origine | modifié) et éditeur de
  définitions JSON avec validation.
- Module checksums génériques (CRC32, sommes 16/32 bits, complément à deux) avec
  avertissement systématique avant export.
- Compilation PyInstaller one-file sans console (`build_windows.spec`, `build.bat`) et
  installateur un clic (`INSTALLER_OPENECU.bat`, Python 3.11.9 32 bits).
