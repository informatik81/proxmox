---
sidebar_position: 6
---

# Fonctionnalités avancées de Proxmox Backup Server

Ce document présente les fonctionnalités avancées de Proxmox Backup Server (PBS) qui permettent d'optimiser votre infrastructure de sauvegarde et de l'adapter à des besoins spécifiques.

## Réplication des sauvegardes

La réplication permet de copier automatiquement vos sauvegardes vers un autre serveur PBS pour une protection supplémentaire.

### Configuration de la réplication

1. Dans l'interface web de PBS, accédez à **Datastore → [Nom du datastore] → Réplication**
2. Cliquez sur **Ajouter**
3. Configurez les paramètres suivants:
   - **ID**: Identifiant unique pour la tâche de réplication
   - **Serveur cible**: Adresse du serveur PBS distant
   - **Datastore cible**: Datastore de destination sur le serveur distant
   - **Planification**: Quand exécuter la réplication (format cron)
   - **Sélection**: Quelles sauvegardes répliquer
   - **Bande passante**: Limite de bande passante (optionnel)
4. Cliquez sur **Créer**

### Authentification pour la réplication

Pour configurer l'authentification entre les serveurs PBS:

```bash
# Sur le serveur source, créez un fichier de configuration pour le serveur distant
proxmox-backup-client config create --fingerprint "XX:XX:XX:XX:XX:XX:XX:XX" target.pbs.example.com:8007 sync-user

# Créez un token d'API pour l'authentification
proxmox-backup-client api-token create sync-user@pam replication-token --comment "Token pour la réplication"
```

### Vérification de la réplication

Pour vérifier l'état de la réplication:

1. Accédez à **Datastore → [Nom du datastore] → Réplication**
2. Consultez la colonne **Statut** pour chaque tâche
3. Cliquez sur **Journal** pour voir les détails des exécutions précédentes

## Chiffrement des sauvegardes

PBS offre un chiffrement de bout en bout pour protéger vos données sensibles.

### Configuration du chiffrement

#### Chiffrement au niveau du datastore

1. Lors de la création d'un datastore, activez l'option **Chiffrement**
2. Définissez une phrase secrète forte
3. Sauvegardez la clé de récupération dans un endroit sûr

#### Chiffrement côté client

Pour un chiffrement avant transfert:

```bash
# Création d'une clé de chiffrement
proxmox-backup-client key create /path/to/key.enc

# Sauvegarde avec chiffrement
proxmox-backup-client backup --encrypt-key /path/to/key.enc /source backup-user@pbs:datastore/backup-name
```

### Restauration de sauvegardes chiffrées

```bash
# Restauration avec déchiffrement
proxmox-backup-client restore --keyfile /path/to/key.enc backup-user@pbs:datastore/backup-name /destination
```

### Rotation des clés de chiffrement

Pour renforcer la sécurité, vous pouvez effectuer une rotation des clés:

1. Créez une nouvelle clé de chiffrement
2. Reconfigurez le datastore avec la nouvelle clé
3. Toutes les nouvelles sauvegardes utiliseront la nouvelle clé
4. Les anciennes sauvegardes restent accessibles avec l'ancienne clé

## Authentification avancée

### Configuration de l'authentification à deux facteurs (2FA)

#### TOTP (Time-based One-Time Password)

1. Dans l'interface web, accédez à **Configuration → Utilisateurs**
2. Sélectionnez l'utilisateur et cliquez sur **TFA**
3. Cliquez sur **Ajouter** et sélectionnez **TOTP**
4. Scannez le code QR avec une application comme Google Authenticator
5. Entrez le code généré pour confirmer

#### WebAuthn (YubiKey et autres dispositifs)

1. Dans l'interface web, accédez à **Configuration → Utilisateurs**
2. Sélectionnez l'utilisateur et cliquez sur **TFA**
3. Cliquez sur **Ajouter** et sélectionnez **WebAuthn**
4. Suivez les instructions pour enregistrer votre dispositif

### Tokens d'API

Les tokens d'API permettent l'automatisation sans exposer les mots de passe:

```bash
# Création d'un token d'API
proxmox-backup-client api-token create user@pam token-name

# Utilisation du token
proxmox-backup-client --api-token-name token-name status
```

## Sauvegarde de serveurs physiques

PBS peut sauvegarder des serveurs physiques en plus des environnements virtualisés.

### Installation du client sur un serveur Linux

```bash
# Debian/Ubuntu
apt install proxmox-backup-client

# RHEL/CentOS/Fedora
dnf install proxmox-backup-client
```

### Configuration des sauvegardes de fichiers

```bash
# Configuration du client
proxmox-backup-client config create backup.pbs.example.com:8007 backup-user

# Sauvegarde d'un répertoire
proxmox-backup-client backup /etc /var/log backup-user@pbs:datastore/server-name
```

### Sauvegarde de bases de données

#### MySQL/MariaDB

```bash
#!/bin/bash
# Script de sauvegarde MySQL

# Dump de la base de données
mysqldump --all-databases > /tmp/mysql-backup.sql

# Sauvegarde vers PBS
proxmox-backup-client backup /tmp/mysql-backup.sql backup-user@pbs:datastore/mysql-backup

# Nettoyage
rm /tmp/mysql-backup.sql
```

#### PostgreSQL

```bash
#!/bin/bash
# Script de sauvegarde PostgreSQL

# Dump de la base de données
pg_dumpall -U postgres > /tmp/postgres-backup.sql

# Sauvegarde vers PBS
proxmox-backup-client backup /tmp/postgres-backup.sql backup-user@pbs:datastore/postgres-backup

# Nettoyage
rm /tmp/postgres-backup.sql
```

## Automatisation avec l'API REST

L'API REST de PBS permet d'automatiser toutes les opérations.

### Exemples d'utilisation de l'API

#### Authentification et obtention d'un ticket

```bash
# Obtention d'un ticket d'authentification
curl -k -d "username=root@pam&password=votremotdepasse" \
  https://pbs.example.com:8007/api2/json/access/ticket
```

#### Lister les sauvegardes

```bash
# Lister les sauvegardes d'un datastore
curl -k -b "PBSAuthCookie=VOTRE_TICKET" \
  https://pbs.example.com:8007/api2/json/datastore/votre-datastore/snapshots
```

#### Déclencher une sauvegarde via l'API

```bash
# Créer une tâche de sauvegarde
curl -k -b "PBSAuthCookie=VOTRE_TICKET" -X POST \
  https://pbs.example.com:8007/api2/json/nodes/localhost/vzdump \
  -d "vmid=100&storage=pbs&mode=snapshot"
```

### Intégration avec des outils d'orchestration

#### Ansible

Exemple de playbook Ansible pour gérer PBS:

```yaml
---
- name: Configurer Proxmox Backup Server
  hosts: pbs_servers
  tasks:
    - name: Créer un datastore
      uri:
        url: "https://{{ pbs_host }}:8007/api2/json/admin/datastore"
        method: POST
        body_format: form-urlencoded
        body:
          name: "{{ datastore_name }}"
          path: "{{ datastore_path }}"
          comment: "Créé par Ansible"
        headers:
          Cookie: "PBSAuthCookie={{ auth_ticket }}"
        validate_certs: no
      register: result
```

## Optimisation des performances

### Configuration du cache

PBS utilise un cache pour accélérer les opérations de déduplication:

1. Dans l'interface web, accédez à **Configuration → Cache**
2. Configurez la taille du cache en fonction de votre RAM disponible
3. Recommandation: allouez 50% de la RAM disponible au cache pour des performances optimales

### Optimisation du réseau

#### Configuration de la bande passante

Pour limiter l'utilisation de la bande passante:

```bash
# Limitation à 50 MB/s
proxmox-backup-client backup --bandwidth-limit 50 /source backup-user@pbs:datastore/backup-name
```

#### Compression réseau

PBS utilise la compression pour réduire le trafic réseau. Vous pouvez ajuster le niveau de compression:

```bash
# Compression maximale (plus lent mais moins de données transférées)
proxmox-backup-client backup --compress zstd-max /source backup-user@pbs:datastore/backup-name

# Compression rapide (plus rapide mais plus de données transférées)
proxmox-backup-client backup --compress zstd-fast /source backup-user@pbs:datastore/backup-name
```

### Optimisation du stockage

#### Configuration ZFS

Si vous utilisez ZFS comme système de fichiers sous-jacent:

```bash
# Création d'un pool ZFS optimisé pour PBS
zpool create -o ashift=12 backup raidz2 /dev/sda /dev/sdb /dev/sdc /dev/sdd

# Création d'un dataset avec compression
zfs create -o compression=lz4 -o recordsize=128k backup/datastore1
```

## Surveillance avancée

### Intégration avec Prometheus

PBS expose des métriques au format Prometheus:

1. Accédez à **Configuration → Metrics Server**
2. Activez le serveur de métriques
3. Configurez Prometheus pour scraper l'endpoint `/metrics`

Exemple de configuration Prometheus:

```yaml
scrape_configs:
  - job_name: 'proxmox-backup'
    static_configs:
      - targets: ['pbs.example.com:8007']
    scheme: https
    tls_config:
      insecure_skip_verify: true
    metrics_path: /api2/json/metrics/prometheus
    params:
      authkey: ['VOTRE_CLE_AUTH']
```

### Alertes personnalisées

Configuration d'alertes basées sur les métriques:

```yaml
# Exemple de règle d'alerte Prometheus
groups:
- name: proxmox-backup
  rules:
  - alert: DatastoreNearlyFull
    expr: proxmox_backup_datastore_usage_ratio > 0.85
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Datastore presque plein"
      description: "Le datastore {{ $labels.datastore }} est utilisé à {{ $value | humanizePercentage }}"
```

## Stratégies de sauvegarde avancées

### Sauvegarde différentielle et incrémentielle

PBS utilise automatiquement la déduplication pour optimiser les sauvegardes successives. Vous pouvez configurer différentes stratégies:

1. **Sauvegarde complète périodique**: Effectuez une sauvegarde complète hebdomadaire
2. **Sauvegardes incrémentielles quotidiennes**: Utilisez la déduplication pour des sauvegardes rapides

### Politiques de rétention avancées

Exemple de configuration de rétention complexe:

```bash
# Configuration de rétention avancée
proxmox-backup-client prune backup-user@pbs:datastore/backup-name \
  --keep-last 7 \
  --keep-hourly 24 \
  --keep-daily 30 \
  --keep-weekly 4 \
  --keep-monthly 12 \
  --keep-yearly 3
```

### Tests de restauration automatisés

Script pour tester régulièrement la restauration:

```bash
#!/bin/bash
# Test de restauration automatisé

# Restauration vers un répertoire temporaire
proxmox-backup-client restore backup-user@pbs:datastore/backup-name /tmp/restore-test

# Vérification de l'intégrité
if [ -f /tmp/restore-test/fichier-critique.dat ]; then
  echo "Test de restauration réussi"
  exit 0
else
  echo "Test de restauration échoué"
  exit 1
fi
```

## Scénarios de reprise après sinistre

### Restauration complète d'un serveur PBS

En cas de perte totale du serveur PBS:

1. Installez un nouveau serveur PBS
2. Restaurez la configuration depuis une sauvegarde
3. Reconnectez les disques de stockage si disponibles
4. Reconstruisez les index si nécessaire

```bash
# Reconstruction de l'index d'un datastore
proxmox-backup-manager datastore index --rebuild votre-datastore
```

### Récupération de sauvegardes chiffrées

Si vous avez perdu la phrase secrète mais avez la clé de récupération:

```bash
# Restauration avec la clé de récupération
proxmox-backup-client restore --keyfile /path/to/recovery.key backup-user@pbs:datastore/backup-name /destination
```

### Plan de continuité d'activité

Exemple de plan de continuité:

1. **Serveur PBS principal**: Sauvegarde quotidienne des VMs critiques
2. **Serveur PBS secondaire**: Réplication des sauvegardes critiques
3. **Stockage hors site**: Réplication mensuelle vers un site distant
4. **Documentation**: Procédures de restauration documentées et testées
5. **Formation**: Personnel formé aux procédures de restauration

## Conclusion

Proxmox Backup Server offre un ensemble complet de fonctionnalités avancées qui permettent de construire une infrastructure de sauvegarde robuste, sécurisée et adaptée à vos besoins spécifiques. En exploitant ces fonctionnalités, vous pouvez optimiser l'utilisation des ressources, automatiser les processus et garantir la disponibilité de vos données en cas d'incident.