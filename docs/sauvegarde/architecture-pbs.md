---
sidebar_position: 5
---

# Architecture de Proxmox Backup Server

Ce document détaille l'architecture technique de Proxmox Backup Server (PBS) et explique comment ses différents composants fonctionnent ensemble pour fournir une solution de sauvegarde robuste et efficace.

## Vue d'ensemble de l'architecture

Proxmox Backup Server est construit sur une architecture moderne qui combine plusieurs technologies avancées pour offrir performance, fiabilité et sécurité. L'architecture globale peut être divisée en plusieurs couches:

1. **Couche système** - Basée sur Debian GNU/Linux
2. **Couche stockage** - Gestion des datastores et du système de fichiers
3. **Couche services** - Daemons et services qui gèrent les opérations
4. **Couche interface** - API REST et interface web
5. **Couche client** - Outils clients pour interagir avec le serveur

## Composants principaux

### Système de base

PBS est construit sur Debian GNU/Linux, ce qui lui confère stabilité et sécurité. Les composants clés incluent:

- **Noyau Linux** - Optimisé pour les opérations d'E/S intensives
- **systemd** - Gestion des services et journalisation
- **rustc** - La plupart des composants sont écrits en Rust pour la sécurité et la performance

### Moteur de stockage

Le moteur de stockage de PBS est conçu pour être hautement efficace et fiable:

- **Datastore** - Conteneur logique pour les sauvegardes
- **Chunk Store** - Stockage des blocs de données dédupliqués
- **Index** - Structures d'indexation pour la recherche rapide des chunks

#### Déduplication

La déduplication dans PBS fonctionne au niveau des blocs variables:

1. Les données sont divisées en chunks de taille variable (4K à 16M)
2. Un hachage cryptographique (SHA-256) est calculé pour chaque chunk
3. Les chunks identiques ne sont stockés qu'une seule fois
4. Un index maintient les références entre les fichiers et les chunks

Cette approche permet d'économiser jusqu'à 90% d'espace disque dans des environnements virtualisés où de nombreuses VM partagent des données similaires.

#### Compression

PBS prend en charge plusieurs algorithmes de compression:

- **zstd** (par défaut) - Bon équilibre entre vitesse et taux de compression
- **lz4** - Compression très rapide mais moins efficace
- **none** - Pas de compression, utile pour les données déjà compressées

La compression est appliquée après la déduplication pour maximiser l'efficacité.

### Services et daemons

PBS utilise plusieurs services pour gérer les différentes fonctionnalités:

- **proxmox-backup-proxy** - Service frontal qui gère les connexions HTTP/HTTPS
- **proxmox-backup** - Service principal qui gère les opérations de sauvegarde
- **proxmox-backup-banner** - Service d'affichage de la bannière SSH
- **proxmox-backup-daily-update** - Service de mise à jour quotidienne

### API REST

Toutes les fonctionnalités de PBS sont accessibles via une API REST complète:

- Authentification basée sur les jetons ou les cookies
- Format JSON pour toutes les requêtes et réponses
- Documentation interactive disponible via l'interface web
- Support de l'authentification à deux facteurs

### Interface web

L'interface web de PBS est construite avec:

- **ExtJS** - Framework JavaScript pour l'interface utilisateur
- **Proxmox Web UI Framework** - Composants réutilisables
- **WebSocket** - Pour les mises à jour en temps réel

## Flux de données

### Processus de sauvegarde

Le processus de sauvegarde suit ces étapes:

1. **Initialisation** - Le client se connecte au serveur et authentifie
2. **Snapshot** - Pour les VM/CT, un snapshot est créé pour assurer la cohérence
3. **Analyse** - Les fichiers sont analysés et divisés en chunks
4. **Déduplication** - Les chunks sont comparés avec ceux déjà stockés
5. **Transfert** - Seuls les nouveaux chunks sont transférés au serveur
6. **Indexation** - Les références sont mises à jour dans l'index
7. **Finalisation** - Les métadonnées sont enregistrées et le snapshot est supprimé

### Processus de restauration

La restauration suit ce processus:

1. **Sélection** - L'utilisateur sélectionne la sauvegarde à restaurer
2. **Vérification** - L'intégrité des données est vérifiée
3. **Téléchargement** - Les chunks nécessaires sont téléchargés
4. **Reconstruction** - Les fichiers originaux sont reconstruits
5. **Déploiement** - Pour les VM/CT, les disques et configurations sont déployés

## Sécurité

### Chiffrement

PBS offre un chiffrement de bout en bout:

- **Chiffrement au repos** - Les données sont chiffrées avant d'être stockées
- **Chiffrement en transit** - TLS pour toutes les communications
- **Algorithme** - AES-256-GCM pour le chiffrement des chunks
- **Gestion des clés** - Clés maîtres protégées par mot de passe

### Authentification et autorisation

- **Realms** - Support de l'authentification locale (pam) et PBS
- **RBAC** - Contrôle d'accès basé sur les rôles
- **2FA** - Support de TOTP, WebAuthn et YubiKey
- **API Tokens** - Pour l'automatisation sécurisée

## Haute disponibilité et réplication

### Réplication des datastores

PBS permet la réplication des datastores entre serveurs:

1. **Configuration** - Définition des jobs de réplication
2. **Synchronisation** - Transfert incrémental des données
3. **Vérification** - Validation de l'intégrité après réplication

### Stratégies de reprise après sinistre

- **Réplication croisée** - Entre plusieurs sites
- **Serveurs de secours** - Configuration de serveurs PBS de secours
- **Restauration rapide** - Procédures de restauration optimisées

## Optimisation des performances

### Recommandations matérielles

Pour des performances optimales:

- **CPU** - Processeurs multi-cœurs modernes (8+ cœurs recommandés)
- **RAM** - 16 GB minimum pour la déduplication efficace, 32+ GB recommandés
- **Stockage** - Configuration tiered:
  - SSD NVMe pour l'index et le cache
  - SSD SATA pour les métadonnées
  - HDD en RAID pour le stockage de masse
- **Réseau** - 10 Gbps recommandé pour les environnements de production

### Optimisation du système de fichiers

- **ZFS** - Recommandé pour les avantages de compression, snapshots et intégrité
- **XFS** - Alternative performante pour les grands volumes
- **ext4** - Option de base compatible

### Paramètres de réglage

- **Taille du cache** - Ajustement selon la RAM disponible
- **Threads de compression** - Optimisation selon le nombre de cœurs CPU
- **Taille des chunks** - Équilibre entre déduplication et performance

## Intégration avec Proxmox VE

### Configuration du stockage

Intégration native avec Proxmox VE:

1. Ajout du stockage PBS dans la configuration de Proxmox VE
2. Configuration des identifiants et du datastore
3. Sélection comme cible de sauvegarde par défaut

### Automatisation des sauvegardes

- **Tâches planifiées** - Configuration via l'interface de Proxmox VE
- **Hooks** - Scripts pre/post sauvegarde pour les actions personnalisées
- **Cluster** - Gestion centralisée des sauvegardes pour tous les nœuds

## Surveillance et maintenance

### Métriques et journalisation

- **Journaux système** - Accessibles via journalctl
- **Journaux d'application** - Stockés dans /var/log/proxmox-backup/
- **Métriques** - Statistiques d'utilisation, performance et santé

### Alertes et notifications

- **Email** - Notifications par email pour les événements importants
- **Hooks** - Scripts personnalisables pour l'intégration avec d'autres systèmes
- **Syslog** - Intégration avec les systèmes de journalisation centralisés

### Maintenance préventive

- **Vérification d'intégrité** - Détection proactive des corruptions
- **Garbage collection** - Nettoyage automatique des chunks orphelins
- **Pruning** - Suppression des sauvegardes expirées selon la politique de rétention

## Cas d'utilisation avancés

### Sauvegarde de serveurs physiques

PBS peut sauvegarder des serveurs physiques avec l'agent proxmox-backup-client:

1. Installation de l'agent sur le serveur physique
2. Configuration des répertoires à sauvegarder
3. Planification des sauvegardes régulières

### Environnements multi-sites

- **Réplication géographique** - Entre datacenters distants
- **Hiérarchie de stockage** - Combinaison de stockage local et distant
- **Politiques différenciées** - Rétention adaptée selon l'importance des données

### Intégration avec des systèmes tiers

- **API REST** - Pour l'intégration avec des outils de monitoring
- **Hooks** - Pour déclencher des actions dans d'autres systèmes
- **Proxmox Mail Gateway** - Pour des notifications avancées

## Conclusion

L'architecture de Proxmox Backup Server est conçue pour offrir une solution de sauvegarde complète, performante et sécurisée. Sa conception modulaire, son efficacité en termes de stockage et son intégration native avec Proxmox VE en font une solution idéale pour les environnements virtualisés, tout en restant flexible pour d'autres cas d'utilisation.

La compréhension de cette architecture permet aux administrateurs de déployer, configurer et maintenir efficacement leur infrastructure de sauvegarde, en tirant pleinement parti des fonctionnalités avancées offertes par PBS.