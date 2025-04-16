---
sidebar_position: 7
---

# Sécurité de Proxmox Backup Server

Ce document détaille les aspects de sécurité de Proxmox Backup Server (PBS) et fournit des recommandations pour sécuriser votre infrastructure de sauvegarde.

## Principes fondamentaux de sécurité

La sécurité de vos sauvegardes est cruciale car elles contiennent souvent des données sensibles et constituent votre dernière ligne de défense contre les pertes de données. PBS intègre plusieurs mécanismes de sécurité:

- **Chiffrement** - Protection des données au repos et en transit
- **Authentification** - Contrôle d'accès robuste
- **Autorisation** - Permissions granulaires basées sur les rôles
- **Audit** - Journalisation complète des activités
- **Intégrité** - Vérification cryptographique des données

## Sécurisation du système d'exploitation

### Mises à jour de sécurité

Maintenez votre serveur PBS à jour pour bénéficier des derniers correctifs de sécurité:

```bash
# Mise à jour du système
apt update && apt upgrade

# Vérification des mises à jour spécifiques à PBS
apt list --upgradable | grep proxmox-backup
```

Activez les mises à jour automatiques pour les correctifs de sécurité:

```bash
apt install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

+ ### Configuration du pare-feu
+
+ Assurez-vous que votre pare-feu est correctement configuré pour protéger votre serveur contre les accès non autorisés.
+
+ ```bash
+ # Installation du pare-feu
+ apt install ufw
+
+ # Activation du pare-feu
+ ufw enable
+
+ # Configuration des règles de pare-feu
+ ufw allow ssh
+ ufw allow 8007/tcp
+ ```

### Durcissement du système

1. **Minimisez la surface d'attaque**:
   - Désactivez les services inutiles
   - N'installez que les packages nécessaires

2. **Configurez le pare-feu**:

```bash
# Installation de UFW (Uncomplicated Firewall)
apt install ufw

# Configuration de base
ufw default deny incoming
ufw default allow outgoing

# Autoriser SSH et l'interface web PBS
ufw allow 22/tcp
ufw allow 8007/tcp

# Activer le pare-feu
ufw enable
```

3. **Sécurisez SSH**:

Modifiez `/etc/ssh/sshd_config`:

```
PermitRootLogin prohibit-password
PasswordAuthentication no
X11Forwarding no
AllowGroups ssh-users
```

Redémarrez le service SSH:

```bash
systemctl restart sshd
```

## Chiffrement des données

### Chiffrement au repos

PBS offre un chiffrement complet des datastores:

1. **Activation du chiffrement**:
   - Lors de la création d'un datastore, cochez "Activer le chiffrement"
   - Définissez une phrase secrète forte (au moins 16 caractères)
   - Sauvegardez la clé de récupération dans un endroit sécurisé

2. **Gestion des clés**:
   - Stockez les phrases secrètes dans un gestionnaire de mots de passe sécurisé
   - Implémentez une procédure de rotation des clés
   - Établissez un processus de récupération en cas de perte de clé

### Chiffrement en transit

Toutes les communications avec PBS sont chiffrées par TLS:

1. **Certificats TLS**:
   - Par défaut, PBS génère un certificat auto-signé
   - Pour une sécurité renforcée, utilisez un certificat signé par une autorité reconnue

2. **Configuration d'un certificat personnalisé**:

```bash
# Installation du certificat et de la clé privée
cp votre-certificat.pem /etc/proxmox-backup/proxy.pem
cp votre-cle-privee.key /etc/proxmox-backup/proxy.key

# Redémarrage du service proxy
systemctl restart proxmox-backup-proxy
```

3. **Vérification de la configuration TLS**:

```bash
# Vérification de la configuration TLS
openssl s_client -connect localhost:8007 -tls1_2
```

## Authentification et contrôle d'accès

### Authentification forte

1. **Politique de mots de passe**:
   - Exigez des mots de passe complexes (au moins 12 caractères)
   - Implémentez une rotation régulière des mots de passe

2. **Authentification à deux facteurs (2FA)**:
   - TOTP (Google Authenticator, Authy)
   - WebAuthn (YubiKey, clés de sécurité FIDO2)

3. **Configuration de TOTP**:
   - Accédez à **Configuration → Utilisateurs**
   - Sélectionnez l'utilisateur et cliquez sur **TFA**
   - Ajoutez un dispositif TOTP

### Contrôle d'accès basé sur les rôles (RBAC)

PBS utilise un système de permissions granulaires:

1. **Rôles prédéfinis**:
   - `Administrator`: Accès complet à toutes les ressources
   - `Audit`: Lecture seule sur toutes les ressources
   - `DatastoreAdmin`: Gestion complète d'un datastore spécifique
   - `DatastoreAudit`: Lecture seule sur un datastore spécifique
   - `DatastoreBackup`: Création et restauration de sauvegardes
   - `DatastorePowerUser`: Gestion des sauvegardes sans accès à la configuration
   - `DatastoreReader`: Lecture seule des sauvegardes

2. **Création d'un utilisateur avec accès limité**:

```bash
# Création d'un utilisateur de sauvegarde
proxmox-backup-manager user create backup-user@pbs --password "mot-de-passe-complexe"

# Attribution des permissions
proxmox-backup-manager acl update /datastore/votre-datastore DatastoreBackup --auth-id backup-user@pbs
```

### Tokens d'API pour l'automatisation

Utilisez des tokens d'API plutôt que des mots de passe pour l'automatisation:

```bash
# Création d'un token d'API
proxmox-backup-manager api-token create backup-user@pbs automation-token

# Utilisation du token
proxmox-backup-client --api-token-id "backup-user@pbs!automation-token" --api-token-secret "votre-secret" status
```

Bonnes pratiques pour les tokens API:
- Créez des tokens avec le minimum de privilèges nécessaires
- Utilisez un token différent pour chaque système d'automatisation
- Révoqué les tokens inutilisés ou compromis

## Isolation réseau

### Segmentation du réseau

1. **Réseau dédié aux sauvegardes**:
   - Créez un VLAN dédié pour le trafic de sauvegarde
   - Limitez les communications entre ce réseau et les autres segments

2. **Configuration d'interfaces réseau multiples**:

```bash
# Configuration d'une interface dédiée aux sauvegardes
cat > /etc/network/interfaces.d/backup-network.conf << EOF
auto ens19
iface ens19 inet static
    address 10.10.10.1/24
    description "Réseau de sauvegarde"
EOF

# Activation de l'interface
systemctl restart networking
```

### Limitation de l'accès réseau

1. **Restriction par IP**:
   - Limitez l'accès à l'interface web aux adresses IP autorisées

```bash
# Configuration du pare-feu pour limiter l'accès à l'interface web
ufw allow from 192.168.1.0/24 to any port 8007 proto tcp
```

2. **Proxy inverse sécurisé**:
   - Utilisez un proxy inverse (comme nginx) pour ajouter une couche de sécurité supplémentaire
   - Implémentez des en-têtes de sécurité HTTP

## Journalisation et audit

### Configuration de la journalisation

1. **Journaux système**:
   - Les journaux de PBS sont stockés dans `/var/log/proxmox-backup/`
   - Utilisez `journalctl` pour consulter les journaux systemd

```bash
# Consultation des journaux PBS
journalctl -u proxmox-backup -u proxmox-backup-proxy
```

2. **Centralisation des journaux**:
   - Configurez un serveur syslog central pour collecter les journaux
   - Utilisez des outils comme ELK Stack ou Graylog pour l'analyse

```bash
# Installation de rsyslog
apt install rsyslog

# Configuration pour envoyer les journaux à un serveur central
echo "*.* @syslog-server:514" > /etc/rsyslog.d/99-remote.conf

# Redémarrage du service
systemctl restart rsyslog
```

### Audit de sécurité

1. **Surveillance des accès**:
   - Examinez régulièrement les journaux d'authentification
   - Configurez des alertes pour les tentatives d'accès échouées

2. **Vérification des permissions**:
   - Auditez régulièrement les permissions des utilisateurs
   - Supprimez les comptes inutilisés

```bash
# Liste des utilisateurs et de leurs permissions
proxmox-backup-manager user list
proxmox-backup-manager acl list
```

## Protection contre les menaces

### Défense contre les ransomwares

Les sauvegardes sont souvent ciblées par les ransomwares. Protégez-les avec:

1. **Principe WORM (Write Once, Read Many)**:
   - Configurez des politiques de rétention immuables
   - Utilisez des permissions en lecture seule pour les sauvegardes terminées

2. **Isolation des sauvegardes**:
   - Conservez des copies hors ligne ou air-gapped
   - Utilisez la règle 3-2-1: 3 copies, 2 supports différents, 1 copie hors site

3. **Vérification régulière**:
   - Testez la restauration des sauvegardes
   - Vérifiez l'intégrité des données

### Protection contre les attaques par force brute

1. **Fail2ban**:
   - Installez et configurez Fail2ban pour bloquer les tentatives d'accès répétées

```bash
# Installation de Fail2ban
apt install fail2ban

# Configuration pour PBS
cat > /etc/fail2ban/jail.d/proxmox-backup.conf << EOF
[proxmox-backup]
enabled = true
port = 8007
filter = proxmox-backup
logpath = /var/log/proxmox-backup/api.log
maxretry = 3
bantime = 3600
EOF

# Création du filtre
cat > /etc/fail2ban/filter.d/proxmox-backup.conf << EOF
[Definition]
failregex = ^.*authentication failure; rhost=<HOST> user=.*$
ignoreregex =
EOF

# Redémarrage du service
systemctl restart fail2ban
```

## Sauvegarde de la configuration PBS

### Sauvegarde de la configuration système

1. **Sauvegarde des fichiers de configuration**:

```bash
# Création d'une archive de configuration
tar -czf /root/pbs-config-backup.tar.gz /etc/proxmox-backup

# Sauvegarde vers un emplacement externe
scp /root/pbs-config-backup.tar.gz utilisateur@serveur-externe:/chemin/de/sauvegarde/
```

2. **Script de sauvegarde automatique**:

```bash
#!/bin/bash
# Script de sauvegarde de la configuration PBS

BACKUP_DIR="/root/pbs-backups"
DATETIME=$(date +"%Y%m%d-%H%M%S")
BACKUP_FILE="$BACKUP_DIR/pbs-config-$DATETIME.tar.gz"

# Création du répertoire de sauvegarde
mkdir -p $BACKUP_DIR

# Sauvegarde des fichiers de configuration
tar -czf $BACKUP_FILE /etc/proxmox-backup /etc/network/interfaces* /etc/hosts

# Conservation des 10 dernières sauvegardes
ls -t $BACKUP_DIR/pbs-config-*.tar.gz | tail -n +11 | xargs -r rm

echo "Sauvegarde de la configuration terminée: $BACKUP_FILE"
```

### Restauration de la configuration

Procédure de restauration en cas de réinstallation:

1. Installez un nouveau serveur PBS
2. Restaurez les fichiers de configuration:

```bash
# Restauration des fichiers de configuration
tar -xzf pbs-config-backup.tar.gz -C /

# Redémarrage des services
systemctl restart proxmox-backup proxmox-backup-proxy
```

## Bonnes pratiques de sécurité

### Liste de contrôle de sécurité

- [ ] Système d'exploitation à jour
- [ ] Pare-feu configuré
- [ ] Authentification à deux facteurs activée
- [ ] Chiffrement des datastores activé
- [ ] Certificats TLS valides
- [ ] Permissions utilisateurs auditées
- [ ] Journalisation centralisée configurée
- [ ] Sauvegardes de configuration régulières
- [ ] Tests de restauration effectués
- [ ] Documentation des procédures de sécurité

### Audit de sécurité périodique

Effectuez un audit de sécurité complet au moins tous les trimestres:

1. Vérifiez les mises à jour de sécurité
2. Examinez les journaux d'accès
3. Testez la restauration des sauvegardes
4. Vérifiez les permissions des utilisateurs
5. Mettez à jour la documentation

## Conclusion

La sécurité de Proxmox Backup Server repose sur une approche en profondeur combinant chiffrement, authentification forte, contrôle d'accès, isolation réseau et surveillance. En suivant les recommandations de ce document, vous pouvez considérablement renforcer la sécurité de votre infrastructure de sauvegarde et protéger vos données contre les menaces internes et externes.

Rappelez-vous que la sécurité est un processus continu qui nécessite une vigilance constante et des mises à jour régulières pour faire face aux nouvelles menaces.