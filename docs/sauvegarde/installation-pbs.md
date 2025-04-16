---
sidebar_position: 2
---

# Installation de Proxmox Backup Server

Ce guide vous explique comment installer Proxmox Backup Server (PBS) sur votre serveur.

## Prérequis

- Un serveur dédié avec au moins:
  - Processeur 64 bits (Intel EMT64 ou AMD64)
  - 4 GB RAM minimum (8 GB ou plus recommandé pour la déduplication)
  - Disque système pour l'OS (SSD recommandé)
  - Disques de stockage pour les sauvegardes
  - Connexion réseau (1 Gbps minimum recommandé)

## Méthodes d'installation

Il existe deux méthodes principales pour installer Proxmox Backup Server:

1. **Installation à partir de l'ISO** - Installation complète incluant le système d'exploitation
2. **Installation sur Debian** - Installation du package PBS sur une installation Debian existante

## Installation à partir de l'ISO

### Téléchargement de l'ISO

1. Rendez-vous sur le [site officiel de Proxmox](https://www.proxmox.com/en/downloads/proxmox-backup-server)
2. Téléchargez la dernière version de l'ISO Proxmox Backup Server
3. Vérifiez l'intégrité du fichier téléchargé avec la somme de contrôle fournie

### Création d'une clé USB bootable

#### Sous Windows

1. Téléchargez et installez [Rufus](https://rufus.ie/fr/)
2. Insérez une clé USB (8 GB minimum)
3. Lancez Rufus et sélectionnez votre clé USB
4. Cliquez sur "SÉLECTION" et choisissez l'ISO Proxmox Backup Server
5. Cliquez sur "DÉMARRER" et attendez que le processus se termine

#### Sous Linux

```bash
# Remplacez /dev/sdX par le chemin de votre clé USB (attention à ne pas se tromper de périphérique)
# et /chemin/vers/proxmox-backup-server.iso par le chemin de l'ISO téléchargée
dd bs=4M if=/chemin/vers/proxmox-backup-server.iso of=/dev/sdX status=progress oflag=sync
```

### Procédure d'installation

1. Démarrez votre serveur sur la clé USB
2. Sélectionnez "Install Proxmox Backup Server" dans le menu de démarrage
3. Acceptez les conditions d'utilisation
4. Sélectionnez le disque cible pour l'installation
5. Configurez les paramètres régionaux (pays, fuseau horaire, disposition du clavier)
6. Définissez un mot de passe pour l'utilisateur root et une adresse email
7. Configurez les paramètres réseau (nom d'hôte, adresse IP, passerelle, serveur DNS)
8. Vérifiez les paramètres et confirmez l'installation
9. Attendez que l'installation se termine et redémarrez le serveur

## Installation sur Debian

Si vous disposez déjà d'un serveur Debian, vous pouvez installer Proxmox Backup Server en suivant ces étapes:

1. Assurez-vous d'utiliser Debian 12 Bookworm (64 bits)

2. Mettez à jour votre système:

```bash
apt update && apt upgrade -y
```

3. Installez les prérequis:

```bash
apt install -y wget gnupg
```

4. Ajoutez le dépôt Proxmox:

```bash
echo "deb [arch=amd64] http://download.proxmox.com/debian/pbs bookworm pbs-no-subscription" > /etc/apt/sources.list.d/pbs.list
```

5. Ajoutez la clé GPG du dépôt:

```bash
wget https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
```

6. Mettez à jour les dépôts:

```bash
apt update
```

7. Installez Proxmox Backup Server:

```bash
apt install -y proxmox-backup-server
```

## Première connexion

1. Une fois l'installation terminée, accédez à l'interface web via un navigateur:

```
https://IP_DE_VOTRE_SERVEUR:8007
```

2. Connectez-vous avec les identifiants suivants:
   - Utilisateur: `root`
   - Mot de passe: le mot de passe défini lors de l'installation

## Configuration initiale

Après la première connexion, vous devrez:

1. Créer un datastore pour stocker vos sauvegardes
2. Configurer les utilisateurs et les permissions
3. Configurer la rétention des sauvegardes
4. Mettre en place des tâches de vérification d'intégrité

Ces étapes seront détaillées dans la section "Configuration de Proxmox Backup Server".

## Dépannage

### Problèmes de connexion à l'interface web

- Vérifiez que le service est bien démarré: `systemctl status proxmox-backup-proxy`
- Vérifiez que le port 8007 est ouvert dans votre pare-feu
- Vérifiez les journaux: `journalctl -u proxmox-backup-proxy`

### Problèmes d'installation

- Vérifiez que votre matériel répond aux prérequis
- Consultez les journaux d'installation: `less /var/log/syslog`
- Vérifiez l'espace disque disponible: `df -h`