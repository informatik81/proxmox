---
sidebar_position: 8
---

# Dépannage de Proxmox Backup Server

Ce document présente les problèmes courants rencontrés avec Proxmox Backup Server (PBS) et leurs solutions. Il vous aidera à diagnostiquer et résoudre efficacement les incidents sur votre infrastructure de sauvegarde.

## Problèmes d'installation

### Échec de l'installation

**Symptômes**: L'installation de PBS échoue avec des erreurs.

**Solutions**:

1. **Vérifiez les prérequis système**:
   ```bash
   # Vérification de l'architecture
   dpkg --print-architecture
   # Doit retourner "amd64"
   
   # Vérification de la version de Debian
   cat /etc/debian_version
   # Doit être compatible avec Debian 12 Bookworm
   ```

2. **Problèmes de dépendances**:
   ```bash
   # Mise à jour des dépôts
   apt update
   
   # Correction des dépendances cassées
   apt --fix-broken install
   ```

3. **Problèmes de signature de dépôt**:
   ```bash
   # Réinstallation de la clé GPG
   wget https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
   ```

### Erreur lors de la création du datastore

**Symptômes**: Impossible de créer un datastore après l'installation.

**Solutions**:

1. **Vérifiez l'espace disque**:
   ```bash
   df -h
   ```

2. **Vérifiez les permissions**:
   ```bash
   # Le répertoire doit appartenir à l'utilisateur backup
   chown backup:backup /chemin/vers/datastore
   ```

3. **Vérifiez le système de fichiers**:
   ```bash
   # Pour ext4
   e2fsck -f /dev/sdX
   
   # Pour ZFS
   zpool status
   zpool scrub nomdupool
   ```

## Problèmes de connexion

### Impossible d'accéder à l'interface web

**Symptômes**: L'interface web n'est pas accessible sur le port 8007.

**Solutions**:

1. **Vérifiez que le service est en cours d'exécution**:
   ```bash
   systemctl status proxmox-backup-proxy
   
   # Si le service est arrêté
   systemctl start proxmox-backup-proxy
   ```

2. **Vérifiez la configuration réseau**:
   ```bash
   # Vérification de l'écoute sur le port 8007
   ss -tulpn | grep 8007
   
   # Vérification du pare-feu
   iptables -L -n
   ```

3. **Vérifiez les journaux**:
   ```bash
   journalctl -u proxmox-backup-proxy --since today
   ```

4. **Redémarrez le service**:
   ```bash
   systemctl restart proxmox-backup-proxy
   ```

### Problèmes d'authentification

**Symptômes**: Impossible de se connecter malgré des identifiants corrects.

**Solutions**:

1. **Réinitialisation du mot de passe root**:
   ```bash
   proxmox-backup-manager user update root@pam --password
   ```

2. **Problèmes avec l'authentification à deux facteurs**:
   ```bash
   # Désactivation temporaire de la 2FA pour un utilisateur
   proxmox-backup-manager tfa delete root@pam
   ```

3. **Vérifiez les fichiers de configuration d'authentification**:
   ```bash
   cat /etc/proxmox-backup/user.cfg
   ```

## Problèmes de sauvegarde

### Échec des tâches de sauvegarde

**Symptômes**: Les sauvegardes échouent avec des erreurs.

**Solutions**:

1. **Vérifiez l'espace disque**:
   ```bash
   df -h
   
   # Espace disponible dans le datastore
   proxmox-backup-manager datastore status votre-datastore
   ```

2. **Vérifiez les permissions**:
   ```bash
   # Vérification des permissions de l'utilisateur
   proxmox-backup-manager acl list
   ```

3. **Problèmes réseau**:
   ```bash
   # Test de connectivité
   ping pbs.example.com
   
   # Vérification de la connexion au port 8007
   nc -zv pbs.example.com 8007
   ```

4. **Examinez les journaux détaillés**:
   ```bash
   # Sur le serveur PBS
   journalctl -u proxmox-backup --since today
   
   # Sur Proxmox VE
   tail -f /var/log/pve/tasks/index
   ```

### Problèmes de déduplication

**Symptômes**: Taux de déduplication anormalement bas ou erreurs liées à la déduplication.

**Solutions**:

1. **Vérifiez la santé du datastore**:
   ```bash
   proxmox-backup-manager datastore verify votre-datastore
   ```

2. **Reconstruisez l'index**:
   ```bash
   proxmox-backup-manager datastore index --rebuild votre-datastore
   ```

3. **Ajustez la mémoire allouée au cache**:
   ```bash
   # Vérification de la configuration actuelle
   cat /etc/proxmox-backup/config.json | grep memory
   
   # Modification via l'interface web: Configuration → Cache
   ```

### Sauvegardes lentes

**Symptômes**: Les sauvegardes prennent beaucoup plus de temps que prévu.

**Solutions**:

1. **Vérifiez les performances réseau**:
   ```bash
   # Test de bande passante
   iperf3 -c pbs.example.com
   ```

2. **Vérifiez les performances disque**:
   ```bash
   # Test de performance disque
   dd if=/dev/zero of=/chemin/vers/datastore/testfile bs=1G count=1 oflag=direct
   ```

3. **Ajustez les paramètres de compression**:
   ```bash
   # Utilisation d'une compression plus rapide
   proxmox-backup-client backup --compress lz4 /source backup-user@pbs:datastore/backup-name
   ```

4. **Vérifiez l'utilisation des ressources**:
   ```bash
   top
   iostat -x 1
   ```

## Problèmes de restauration

### Échec de restauration

**Symptômes**: Impossible de restaurer une sauvegarde.

**Solutions**:

1. **Vérifiez l'intégrité de la sauvegarde**:
   ```bash
   proxmox-backup-manager snapshot verify votre-datastore:backup-id
   ```

2. **Vérifiez les permissions**:
   ```bash
   # L'utilisateur doit avoir les permissions de restauration
   proxmox-backup-manager acl list
   ```

3. **Problèmes d'espace disque**:
   ```bash
   # Vérifiez l'espace disponible à la destination
   df -h /chemin/de/destination
   ```

4. **Restauration manuelle**:
   ```bash
   # Restauration avec options détaillées
   proxmox-backup-client restore --verbose backup-user@pbs:datastore/backup-id /chemin/destination
   ```

### Problèmes avec les sauvegardes chiffrées

**Symptômes**: Erreurs lors de la restauration de sauvegardes chiffrées.

**Solutions**:

1. **Vérifiez la clé de chiffrement**:
   ```bash
   # Vérification de la clé
   proxmox-backup-client key info /chemin/vers/keyfile
   ```

2. **Utilisez la clé de récupération**:
   ```bash
   # Restauration avec la clé de récupération
   proxmox-backup-client restore --keyfile /chemin/vers/recovery.key backup-user@pbs:datastore/backup-id /destination
   ```

3. **Vérifiez les journaux pour les erreurs de déchiffrement**:
   ```bash
   journalctl -u proxmox-backup --since today | grep -i "decrypt"
   ```

## Problèmes de stockage

### Corruption du datastore

**Symptômes**: Erreurs d'accès au datastore ou corruption signalée.

**Solutions**:

1. **Vérification du datastore**:
   ```bash
   proxmox-backup-manager datastore verify votre-datastore
   ```

2. **Vérification du système de fichiers sous-jacent**:
   ```bash
   # Pour ext4
   e2fsck -f /dev/sdX
   
   # Pour ZFS
   zpool scrub nomdupool
   zpool status
   ```

3. **Reconstruction de l'index**:
   ```bash
   proxmox-backup-manager datastore index --rebuild votre-datastore
   ```

4. **Récupération à partir d'une réplication**:
   Si le datastore est corrompu et que vous avez configuré la réplication, restaurez à partir du serveur de réplication.

### Espace disque insuffisant

**Symptômes**: Erreurs d'espace disque insuffisant.

**Solutions**:

1. **Vérifiez l'utilisation de l'espace**:
   ```bash
   df -h
   proxmox-backup-manager datastore status votre-datastore
   ```

2. **Exécutez un élagage manuel**:
   ```bash
   proxmox-backup-manager prune votre-datastore --dry-run
   proxmox-backup-manager prune votre-datastore
   ```

3. **Exécutez la collecte des déchets**:
   ```bash
   proxmox-backup-manager garbage-collection votre-datastore
   ```

4. **Ajoutez de l'espace de stockage**:
   ```bash
   # Pour ZFS, ajout d'un disque
   zpool add nomdupool /dev/sdX
   ```

## Problèmes de performance

### Utilisation élevée du CPU

**Symptômes**: Utilisation CPU anormalement élevée sur le serveur PBS.

**Solutions**:

1. **Identifiez les processus consommateurs**:
   ```bash
   top
   ps aux --sort=-%cpu | head -10
   ```

2. **Vérifiez les tâches en cours**:
   ```bash
   proxmox-backup-manager task list
   ```

3. **Ajustez les paramètres de compression**:
   Réduisez le niveau de compression si le CPU est le goulot d'étranglement.

4. **Planifiez les tâches intensives pendant les heures creuses**:
   Modifiez la planification des tâches de vérification, élagage et collecte des déchets.

### Problèmes de mémoire

**Symptômes**: Utilisation mémoire élevée ou swapping excessif.

**Solutions**:

1. **Vérifiez l'utilisation de la mémoire**:
   ```bash
   free -h
   ```

2. **Ajustez la taille du cache**:
   ```bash
   # Réduisez la taille du cache si nécessaire
   # Via l'interface web: Configuration → Cache
   ```

3. **Vérifiez les fuites mémoire**:
   ```bash
   # Surveillance de l'utilisation mémoire dans le temps
   watch -n 1 "free -m"
   ```

## Problèmes de réplication

### Échec de la réplication

**Symptômes**: Les tâches de réplication échouent.

**Solutions**:

1. **Vérifiez la connectivité**:
   ```bash
   ping serveur-cible
   nc -zv serveur-cible 8007
   ```

2. **Vérifiez les identifiants**:
   ```bash
   # Test de connexion avec les identifiants
   proxmox-backup-client --repository serveur-cible:8007 status
   ```

3. **Vérifiez les journaux de réplication**:
   ```bash
   journalctl -u proxmox-backup --since today | grep -i "replication"
   ```

4. **Vérifiez l'espace disque sur la cible**:
   ```bash
   # Via SSH sur le serveur cible
   df -h
   ```

### Réplication lente

**Symptômes**: La réplication prend beaucoup plus de temps que prévu.

**Solutions**:

1. **Vérifiez la bande passante réseau**:
   ```bash
   iperf3 -c serveur-cible
   ```

2. **Limitez la bande passante pendant les heures de travail**:
   ```bash
   # Configuration d'une limite de bande passante
   # Via l'interface web: Datastore → Réplication → Modifier → Limite de bande passante
   ```

3. **Optimisez la planification**:
   Planifiez les réplications pendant les périodes de faible activité réseau.

## Problèmes de mise à jour

### Échec de mise à jour

**Symptômes**: Les mises à jour de PBS échouent.

**Solutions**:

1. **Vérifiez les dépendances**:
   ```bash
   apt update
   apt --fix-broken install
   ```

2. **Problèmes de dépôt**:
   ```bash
   # Vérification des sources
   cat /etc/apt/sources.list.d/pbs.list
   
   # Réinstallation du dépôt
   echo "deb [arch=amd64] http://download.proxmox.com/debian/pbs bookworm pbs-no-subscription" > /etc/apt/sources.list.d/pbs.list
   ```

3. **Mise à jour manuelle**:
   ```bash
   apt update
   apt install proxmox-backup-server
   ```

### Problèmes après mise à jour

**Symptômes**: Problèmes de fonctionnement après une mise à jour.

**Solutions**:

1. **Vérifiez les journaux**:
   ```bash
   journalctl -u proxmox-backup --since today
   ```

2. **Redémarrez les services**:
   ```bash
   systemctl restart proxmox-backup proxmox-backup-proxy
   ```

3. **Vérifiez la compatibilité des versions**:
   ```bash
   # Vérification des versions installées
   apt list --installed | grep proxmox-backup
   ```

4. **Retour à une version précédente si nécessaire**:
   ```bash
   apt install proxmox-backup-server=version_précédente
   ```

## Outils de diagnostic

### Collecte d'informations système

```bash
# Informations système complètes
proxmox-backup-debug-info

# Le résultat est enregistré dans /var/tmp/proxmox-backup-debug-info.tar.gz
```

Ce fichier contient des informations précieuses pour le diagnostic:
- Configuration système
- Journaux
- État des services
- Configuration réseau

### Commandes de diagnostic courantes

```bash
# État des services PBS
systemctl status proxmox-backup proxmox-backup-proxy

# Journaux récents
journalctl -u proxmox-backup --since "24 hours ago"

# État des datastores
proxmox-backup-manager datastore status

# Liste des tâches en cours
proxmox-backup-manager task list

# Vérification de la configuration
cat /etc/proxmox-backup/config.json
```

## Récupération d'urgence

### Restauration après une panne matérielle

1. **Installez PBS sur un nouveau serveur**
2. **Reconnectez les disques de stockage si possible**
3. **Importez la configuration**:
   ```bash
   # Restauration de la configuration
   tar -xzf pbs-config-backup.tar.gz -C /
   ```
4. **Reconstruisez les index si nécessaire**:
   ```bash
   proxmox-backup-manager datastore index --rebuild votre-datastore
   ```

### Récupération après corruption de la base de données

```bash
# Arrêt des services
systemctl stop proxmox-backup proxmox-backup-proxy

# Sauvegarde de la base de données corrompue
cp -a /var/lib/proxmox-backup /var/lib/proxmox-backup.bak

# Reconstruction de la base de données
rm -rf /var/lib/proxmox-backup/*.db
systemctl start proxmox-backup

# Reconstruisez les index des datastores
proxmox-backup-manager datastore index --rebuild votre-datastore
```

## Bonnes pratiques pour éviter les problèmes

1. **Surveillance proactive**:
   - Configurez des alertes pour l'espace disque
   - Surveillez les journaux d'erreurs
   - Vérifiez régulièrement l'état des datastores

2. **Maintenance régulière**:
   - Mises à jour système régulières
   - Vérification périodique de l'intégrité des sauvegardes
   - Nettoyage des anciennes sauvegardes

3. **Documentation**:
   - Documentez votre configuration
   - Créez des procédures de récupération
   - Conservez les sauvegardes de configuration

4. **Tests de restauration**:
   - Testez régulièrement la restauration des sauvegardes
   - Simulez des scénarios de récupération d'urgence

## Conclusion

Ce guide de dépannage couvre les problèmes les plus courants rencontrés avec Proxmox Backup Server. En suivant ces procédures de diagnostic et de résolution, vous pourrez maintenir votre infrastructure de sauvegarde en bon état de fonctionnement et résoudre rapidement les incidents lorsqu'ils surviennent.

N'oubliez pas que la prévention est la meilleure approche: une surveillance proactive, une maintenance régulière et des tests de restauration périodiques vous aideront à éviter de nombreux problèmes avant qu'ils ne surviennent.