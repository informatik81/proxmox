---
sidebar_position: 1
---

# Introduction à Proxmox Backup Server

Proxmox Backup Server (PBS) est une solution de sauvegarde d'entreprise optimisée pour l'environnement Proxmox VE. Cette documentation vous guidera à travers l'installation, la configuration et l'utilisation de PBS.

## Qu'est-ce que Proxmox Backup Server?

Proxmox Backup Server est une solution complète de sauvegarde conçue spécifiquement pour fonctionner avec Proxmox Virtual Environment. Il offre:

- **Déduplication et compression** - Économisez de l'espace de stockage grâce à la déduplication au niveau des blocs et à la compression
- **Chiffrement** - Protégez vos données avec un chiffrement de bout en bout
- **Vérification d'intégrité** - Assurez-vous que vos sauvegardes sont intactes et restaurables
- **Interface web intuitive** - Gérez vos sauvegardes facilement via une interface web moderne
- **API REST** - Automatisez vos processus de sauvegarde via l'API

## Architecture de Proxmox Backup Server

Proxmox Backup Server utilise une architecture client-serveur:

- **Serveur de sauvegarde**: Stocke et gère les sauvegardes
- **Client de sauvegarde**: S'exécute sur les hôtes Proxmox VE pour envoyer les données au serveur

## Concepts clés

### Datastore

Un datastore est un emplacement de stockage pour les sauvegardes. Vous pouvez configurer plusieurs datastores sur un serveur PBS, chacun avec ses propres paramètres de rétention et de déduplication.

### Backup

Un backup est une sauvegarde complète d'une machine virtuelle ou d'un conteneur à un moment précis. PBS stocke les backups de manière efficace grâce à la déduplication.

### Snapshot

Un snapshot est une capture instantanée de l'état d'une VM ou d'un conteneur. PBS utilise des snapshots pour créer des sauvegardes cohérentes.

## Prérequis matériels

Pour installer Proxmox Backup Server, vous aurez besoin de:

- Processeur x86_64 (Intel EMT64 ou AMD64)
- 2 GB de RAM minimum (8 GB ou plus recommandé pour la déduplication)
- Disque système pour l'OS (SSD recommandé)
- Disques de stockage pour les sauvegardes
- Connexion réseau (1 Gbps minimum recommandé)

## Avantages par rapport aux solutions traditionnelles

- **Intégration native** avec Proxmox VE
- **Performance optimisée** pour les environnements virtualisés
- **Coût réduit** par rapport aux solutions propriétaires
- **Simplicité d'utilisation** grâce à l'interface web intuitive
- **Flexibilité** dans les options de stockage et de configuration

Dans les sections suivantes, nous explorerons l'installation, la configuration et l'utilisation quotidienne de Proxmox Backup Server.