---
sidebar_position: 1
---

# Installation de Proxmox VE

Ce guide vous explique comment installer Proxmox Virtual Environment sur votre serveur.

## Prérequis

- Un serveur dédié avec au moins:
  - Processeur 64 bits (Intel EMT64 ou AMD64) avec support de virtualisation
  - 2 GB RAM minimum (4 GB ou plus recommandé)
  - Disque dur ou SSD
  - Carte réseau

## Téléchargement de l'ISO

1. Rendez-vous sur le [site officiel de Proxmox](https://www.proxmox.com/en/downloads/proxmox-ve)
2. Téléchargez la dernière version de l'ISO Proxmox VE
3. Vérifiez l'intégrité du fichier téléchargé avec la somme de contrôle fournie

## Création d'une clé USB bootable

### Sous Windows

1. Téléchargez et installez [Rufus](https://rufus.ie/fr/)
2. Insérez une clé USB (8 GB minimum)
3. Lancez Rufus et sélectionnez votre clé USB
4. Cliquez sur "SÉLECTION" et choisissez l'ISO Proxmox VE
5. Cliquez sur "DÉMARRER" et attendez que le processus se termine

### Sous Linux

```bash
sudo dd bs=4M if=/chemin/vers/proxmox-ve_*.iso of=/dev/sdX status=progress oflag=sync