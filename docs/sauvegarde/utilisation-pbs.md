---
sidebar_position: 4
---

# Utilisation de Proxmox Backup Server

Ce guide vous explique comment utiliser Proxmox Backup Server au quotidien pour sauvegarder et restaurer vos machines virtuelles et conteneurs.

## Création de sauvegardes

### Sauvegarde depuis Proxmox VE

La méthode la plus simple pour sauvegarder vos VMs et conteneurs est d'utiliser l'interface de Proxmox VE.

#### Sauvegarde manuelle

1. Dans l'interface de Proxmox VE, sélectionnez la VM ou le conteneur à sauvegarder
2. Cliquez sur **Sauvegarde** dans le menu
3. Cliquez sur **Sauvegarder maintenant**
4. Configurez les options de sauvegarde:
   - **Stockage**: Sélectionnez votre stockage PBS configuré
   - **Mode**: Snapshot (recommandé) ou Arrêt
   - **Compression**: zstd (recommandé)
   - **Mode**: Sauvegarder tous les disques
5. Cliquez sur **Sauvegarder**

#### Planification de sauvegardes automatiques

1. Dans Proxmox VE, accédez à **Datacenter → Sauvegarde**
2. Cliquez sur **Ajouter**
3. Configurez la tâche de sauvegarde:
   - **Stockage**: Sélectionnez votre stockage PBS
   - **Jour de la semaine**: Quand exécuter la sauvegarde
   - **Heure**: À quelle heure exécuter la sauvegarde
   - **Sélection**: Quelles VMs/CTs sauvegarder
   - **Mode**: Snapshot (recommandé)
   - **Compression**: zstd (recommandé)
   - **Envoi par email**: Configuration des notifications
   - **Rétention**: Nombre de sauvegardes à conserver
4. Cliquez sur **Créer**

### Sauvegarde avec l'outil en ligne de commande

Vous pouvez également utiliser l'outil en ligne de commande `proxmox-backup-client` pour des sauvegardes plus flexibles.

#### Configuration du client

```bash
# Configuration des identifiants
proxmox-backup-client config create client.pbs.example.com:8007 backup-user --password

# Vérification de la connexion
proxmox-backup-client status
```

#### Sauvegarde d'un répertoire

```bash
proxmox-backup-client backup /chemin/vers/dossier backup-user@pbs:datastore/nom-sauvegarde
```

#### Sauvegarde d'une VM Proxmox

```bash
proxmox-backup-client backup vm:100 backup-user@pbs:datastore/vm-100
```

## Restauration de sauvegardes

### Restauration depuis Proxmox VE

1. Dans l'interface de Proxmox VE, accédez à **Stockage → [Stockage PBS]**
2. Sélectionnez la sauvegarde à restaurer
3. Cliquez sur **Restaurer**
4. Configurez les options de restauration:
   - **VM ID**: ID de la VM à créer (ou existante à écraser)
   - **Stockage**: Stockage où restaurer les disques
   - **Options**: Restaurer avec/sans configuration réseau, etc.
5. Cliquez sur **Restaurer**

### Restauration partielle

Vous pouvez restaurer des fichiers individuels à partir d'une sauvegarde:

1. Dans l'interface de PBS, accédez à **Datastore → [Datastore] → Content**
2. Sélectionnez la sauvegarde
3. Naviguez dans les fichiers
4. Sélectionnez le fichier à restaurer et cliquez sur **Télécharger**

### Restauration avec l'outil en ligne de commande

```bash
# Restauration complète
proxmox-backup-client restore backup-user@pbs:datastore/nom-sauvegarde /chemin/destination

# Restauration de fichiers spécifiques
proxmox-backup-client restore backup-user@pbs:datastore/nom-sauvegarde /chemin/destination --filter="chemin/du/fichier"
```

## Vérification des sauvegardes

### Vérification manuelle

1. Dans l'interface de PBS, accédez à **Datastore → [Datastore] → Content**
2. Sélectionnez la sauvegarde à vérifier
3. Cliquez sur **Vérifier**
4. Attendez que la vérification se termine et consultez le résultat

### Vérification automatique

Les tâches de vérification configurées s'exécuteront automatiquement selon la planification définie. Vous pouvez consulter les résultats dans:

1. Accédez à **Datastore → [Datastore] → Vérification**
2. Consultez l'onglet **Tâches** pour voir les vérifications planifiées
3. Consultez l'onglet **Journal** pour voir les résultats des vérifications

## Gestion des sauvegardes

### Suppression manuelle

1. Dans l'interface de PBS, accédez à **Datastore → [Datastore] → Content**
2. Sélectionnez la sauvegarde à supprimer
3. Cliquez sur **Supprimer**
4. Confirmez la suppression

### Élagage automatique

L'élagage automatique supprime les anciennes sauvegardes selon la politique de rétention configurée:

1. L'élagage s'exécute selon la planification définie dans la configuration du datastore
2. Vous pouvez déclencher un élagage manuel en accédant à **Datastore → [Datastore] → Content** et en cliquant sur **Prune**
3. Consultez les journaux d'élagage dans **Datastore → [Datastore] → Prune**

## Surveillance et maintenance

### Surveillance de l'espace disque

1. Dans l'interface de PBS, accédez à **Dashboard**
2. Consultez les graphiques d'utilisation du disque
3. Configurez des alertes d'espace disque dans **Configuration → Notifications**

### Maintenance du datastore

#### Garbage Collection

La collecte des déchets (garbage collection) libère l'espace occupé par des données qui ne sont plus référencées:

1. Elle s'exécute automatiquement selon la planification définie
2. Vous pouvez la déclencher manuellement en accédant à **Datastore → [Datastore] → Garbage Collection** et en cliquant sur **Démarrer la collecte des déchets**

#### Maintenance du serveur

1. Mettez régulièrement à jour PBS avec:

```bash
apt update && apt upgrade
```

2. Surveillez les journaux système:

```bash
journalctl -u proxmox-backup
```

## Bonnes pratiques

### Stratégie de sauvegarde

- **Règle 3-2-1**: Conservez au moins 3 copies de vos données, sur 2 types de supports différents, avec 1 copie hors site
- **Sauvegardes régulières**: Planifiez des sauvegardes quotidiennes pour les données critiques
- **Tests de restauration**: Testez régulièrement la restauration de vos sauvegardes
- **Documentation**: Documentez votre stratégie de sauvegarde et les procédures de restauration

### Sécurité

- Utilisez le chiffrement pour les données sensibles
- Limitez l'accès au serveur PBS avec un pare-feu
- Utilisez des mots de passe forts et l'authentification à deux facteurs si disponible
- Mettez régulièrement à jour le système et les packages

### Performance

- Utilisez des disques SSD pour le cache et les métadonnées
- Configurez la compression en fonction de vos besoins (équilibre entre CPU et espace disque)
- Planifiez les sauvegardes pendant les heures creuses
- Utilisez un réseau dédié pour les sauvegardes si possible