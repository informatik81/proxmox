# Changelog — OpenECU Studio

Toutes les évolutions notables du projet sont documentées ici (format « Keep a Changelog »).

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
