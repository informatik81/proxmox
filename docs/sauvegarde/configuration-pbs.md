---
sidebar_position: 3
---

# Configuration de Proxmox Backup Server

Après avoir installé Proxmox Backup Server, vous devez le configurer pour commencer à l'utiliser. Ce guide vous explique les étapes essentielles de configuration.

## Configuration des datastores

Un datastore est l'emplacement où vos sauvegardes seront stockées. Vous pouvez créer plusieurs datastores avec différentes configurations.

### Création d'un datastore

1. Dans l'interface web de PBS, accédez à **Datastore** dans le menu latéral
2. Cliquez sur **Ajouter**
3. Remplissez les champs suivants:
   - **Nom**: Un nom unique pour votre datastore (ex: backup-vms)
   - **ID du datastore**: Un identifiant unique (généralement le même que le nom)
   - **Commentaire**: Une description optionnelle
   - **Répertoire**: Le chemin où les sauvegardes seront stockées
   - **GC Schedule**: Planification du nettoyage (garbage collection)
   - **Prune Schedule**: Planification de l'élagage des anciennes sauvegardes
4. Cliquez sur **Créer**

### Options avancées des datastores

- **Déduplication**: Activée par défaut, économise de l'espace en ne stockant qu'une seule fois les données identiques
- **Compression**: Réduit la taille des sauvegardes (options: zstd, lz4, none)
- **Chiffrement**: Protège vos données avec un chiffrement AES-256

## Gestion des utilisateurs et permissions

PBS utilise un système de contrôle d'accès basé sur les rôles pour gérer les permissions.

### Création d'un utilisateur

1. Accédez à **Configuration → Utilisateurs** dans le menu latéral
2. Cliquez sur **Ajouter**
3. Remplissez les informations de l'utilisateur:
   - **Utilisateur**: Nom d'utilisateur
   - **Realm**: Domaine d'authentification (pam, pbs)
   - **Mot de passe**: Mot de passe sécurisé
   - **Email**: Adresse email pour les notifications
   - **Commentaire**: Description optionnelle
4. Cliquez sur **Créer**

### Attribution des permissions

1. Accédez à **Configuration → Permissions** dans le menu latéral
2. Cliquez sur **Ajouter**
3. Sélectionnez:
   - **Chemin**: Ressource à laquelle accorder l'accès (ex: /datastore/backup-vms)
   - **Utilisateur/Groupe**: L'utilisateur ou groupe concerné
   - **Rôle**: Niveau d'accès (ex: DatastoreAdmin, DatastoreAudit, DatastoreBackup)
   - **Propager**: Si les permissions doivent s'appliquer aux sous-ressources
4. Cliquez sur **Créer**

## Configuration de la rétention des sauvegardes

La politique de rétention définit combien de temps vos sauvegardes sont conservées.

### Configuration de la rétention

1. Accédez à **Datastore → [Nom du datastore] → Configuration**
2. Cliquez sur l'onglet **Prune**
3. Définissez les règles de conservation:
   - **Conserver les dernières**: Nombre de sauvegardes récentes à conserver
   - **Conserver par heure**: Nombre de sauvegardes horaires à conserver
   - **Conserver par jour**: Nombre de sauvegardes quotidiennes à conserver
   - **Conserver par semaine**: Nombre de sauvegardes hebdomadaires à conserver
   - **Conserver par mois**: Nombre de sauvegardes mensuelles à conserver
   - **Conserver par année**: Nombre de sauvegardes annuelles à conserver
4. Cliquez sur **Appliquer**

## Configuration des tâches de vérification

Les tâches de vérification s'assurent que vos sauvegardes sont intactes et restaurables.

### Création d'une tâche de vérification

1. Accédez à **Datastore → [Nom du datastore] → Vérification**
2. Cliquez sur **Ajouter**
3. Configurez la tâche:
   - **ID**: Identifiant unique pour la tâche
   - **Planification**: Quand exécuter la vérification (format cron)
   - **Sélection**: Quelles sauvegardes vérifier (dernière, toutes)
   - **Ignorer vérifiées**: Ignorer les sauvegardes déjà vérifiées
   - **Notification**: Configuration des notifications en cas d'erreur
4. Cliquez sur **Créer**

## Configuration du réseau

### Configuration des interfaces réseau

1. Accédez à **Configuration → Réseau** dans le menu latéral
2. Sélectionnez l'interface à configurer
3. Cliquez sur **Modifier**
4. Configurez les paramètres réseau:
   - **Mode IP**: DHCP ou Static
   - **Adresse IP/CIDR**: Adresse IP et masque de sous-réseau
   - **Passerelle**: Passerelle par défaut
   - **DNS**: Serveurs DNS
5. Cliquez sur **Appliquer la configuration**

### Configuration du pare-feu

1. Accédez à **Configuration → Pare-feu** dans le menu latéral
2. Activez le pare-feu si nécessaire
3. Ajoutez des règles pour autoriser le trafic nécessaire:
   - Port 8007 pour l'interface web
   - Port 8007 pour l'API REST

## Configuration des notifications

### Configuration des emails

1. Accédez à **Configuration → Notifications** dans le menu latéral
2. Configurez le serveur SMTP:
   - **Serveur SMTP**: Adresse du serveur de messagerie
   - **Port**: Port du serveur SMTP (généralement 25, 465 ou 587)
   - **Authentification**: Si nécessaire, activez et fournissez les identifiants
   - **Chiffrement**: TLS ou SSL selon votre serveur
   - **Expéditeur**: Adresse d'expédition des emails
3. Cliquez sur **Appliquer**

## Intégration avec Proxmox VE

Pour utiliser PBS avec Proxmox VE, vous devez configurer le stockage de sauvegarde dans Proxmox VE.

1. Dans l'interface de Proxmox VE, accédez à **Datacenter → Stockage**
2. Cliquez sur **Ajouter → PBS**
3. Configurez le stockage:
   - **ID**: Identifiant unique pour le stockage
   - **Serveur**: Adresse IP ou nom d'hôte du serveur PBS
   - **Port**: 8007 (par défaut)
   - **Datastore**: Nom du datastore PBS
   - **Utilisateur**: Utilisateur PBS avec droits de sauvegarde
   - **Mot de passe**: Mot de passe de l'utilisateur
   - **Fingerprint**: Empreinte du certificat SSL (optionnel mais recommandé)
4. Cliquez sur **Ajouter**

Vous pouvez maintenant créer des tâches de sauvegarde dans Proxmox VE qui utiliseront votre serveur PBS comme destination.