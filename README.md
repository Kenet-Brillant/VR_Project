# VR_Project — Système Unity × MQTT × Python

> **Auteur :** Brillant Kenet FOUANA — ESTIA 2026  
> **Dépôt :** https://github.com/Kenet-Brillant/VR_Project

---

## 📋 Table des matières

1. [Présentation du projet](#présentation-du-projet)
2. [Architecture globale](#architecture-globale)
3. [Prérequis](#prérequis)
4. [Structure des dossiers](#structure-des-dossiers)
5. [Installation](#installation)
6. [Lancer le système complet](#lancer-le-système-complet)
7. [Jeu des boules](#jeu-des-boules)
8. [Jeu d'obstacles](#jeu-dobstacles)
9. [Logger Python](#logger-python)
10. [Controller Gradio](#controller-gradio)
11. [Main Controller (génération automatique)](#main-controller)
12. [Stress Test](#stress-test)
13. [Utiliser les fichiers MQTT sur un autre projet Unity](#utiliser-les-fichiers-mqtt-sur-un-autre-projet-unity)
14. [Résultats obtenus](#résultats-obtenus)

---

## Présentation du projet

Ce projet connecte des jeux développés sous **Unity** à une infrastructure de communication **MQTT**, afin de :

- **Logger** (enregistrer) toutes les données de jeu en temps réel dans des fichiers JSON
- **Contrôler** les paramètres du jeu à distance depuis une interface web
- **Monitorer** les performances (FPS) pendant des tests de charge

Deux jeux Unity ont été connectés :
- **Jeu des boules** : des sphères apparaissent en cercle, le joueur doit toutes les cliquer
- **Jeu d'obstacles** : le joueur esquive des obstacles, un score est calculé

---

## Architecture globale

```
┌─────────────────┐        ┌──────────────────┐        ┌────────────────────┐
│   App Unity     │──────▶ │   Broker MQTT    │──────▶ │   Logger Python    │
│  (Jeu C#)       │        │ devweb.estia.fr  │        │   logger.py        │
│                 │ ◀───── │    port 1883     │ ◀───── │   logs/*.json      │
└─────────────────┘        └──────────────────┘        └────────────────────┘
                                    ▲
                                    │
                           ┌────────────────────┐
                           │  Controller Python │
                           │  (Interface Gradio)│
                           │  controller.py     │
                           └────────────────────┘
```

**Flux événements (Unity → Broker → Logger) :**
Unity publie chaque action du joueur sur un topic MQTT. Le Logger Python s'abonne et sauvegarde tout.

**Flux commandes (Controller → Broker → Unity) :**
L'interface web Gradio publie des commandes sur un topic. Unity les reçoit et modifie le jeu en temps réel.

**Topics MQTT :**

| Jeu | Topic événements | Topic commandes |
|-----|-----------------|-----------------|
| Boules | `jeu/boules/evenement` | `unity/commands` |
| Obstacles | `jeu/obstacle/evenement` | `unity/obstacle/commands` |
| Config | `jeu/config` | — |
| Stress | `jeu/stress/fps` | — |

---

## Prérequis

### Logiciels
- **Unity 6** (version 6000.0.63f1 ou supérieure)
- **Python 3.8+**
- **Git**

### Bibliothèques Python
```bash
pip install paho-mqtt gradio
```

### Accès broker MQTT
- **Host :** `devweb.estia.fr`
- **Port :** `1883`
- **Username :** `estia`
- **Password :** `*aZ9#r8X7`

> ⚠️ Le broker doit être accessible depuis votre réseau. Testez avec un client MQTT si nécessaire.

---

## Structure des dossiers

```
VR_Project/
│
├── boules/                     ← Projet Unity jeu des boules
│   └── Assets/script/
│       ├── MQTTgene/           ← Fichiers MQTT génériques
│       │   ├── MQTTClient.cs
│       │   ├── MQTTPublisher.cs
│       │   ├── MQTTReceiver.cs
│       │   └── MQTTController.cs
│       ├── CircleManager.cs    ← Logique du jeu des boules
│       └── SphereClick.cs      ← Détection de clic
│
├── obstacles/                  ← Projet Unity jeu d'obstacles
│   └── Assets/script/
│       ├── MQTTgene/           ← Mêmes fichiers MQTT génériques
│       ├── GameManager.cs      ← Score, Game Over, MQTT
│       ├── PlayerController.cs ← Déplacements joueur
│       ├── ObstacleSpawner.cs  ← Spawn des obstacles
│       └── ObstacleMovement.cs ← Déplacement obstacles
│
├── stress/
│   └── UnityStressReporter.cs  ← Script Unity pour mesurer les FPS
│
├── logs/                       ← Fichiers JSON générés par le logger
│   ├── joueur_1.json
│   ├── joueur_1_2.json
│   └── ...
│
├── logger.py                   ← Logger Python générique (v2)
├── main_controller.py          ← Génère automatiquement le controller
├── unity_stress_test.py        ← Script de stress test
├── controller_boules.py        ← Controller Gradio (généré automatiquement)
├── config_boules.json          ← Config du stress test pour les boules
└── config_obstacles.json       ← Config du stress test pour les obstacles
```

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Kenet-Brillant/VR_Project.git
cd VR_Project
```

### 2. Installer les dépendances Python

```bash
pip install paho-mqtt gradio
```

### 3. Ouvrir les projets Unity

- Ouvrir **Unity Hub**
- **Add project from disk**
- Sélectionner le dossier `boules/` pour le jeu des boules
- Sélectionner le dossier `obstacles/` pour le jeu d'obstacles

> Les fichiers MQTT dans `Assets/script/MQTTgene/` sont déjà en place — aucune installation de package supplémentaire n'est nécessaire.

---

## Lancer le système complet

### Ordre de démarrage obligatoire

```
1. python logger.py          (Terminal 1)
2. python main_controller.py (Terminal 2)
3. Lancer Unity ▶️
4. Cliquer "Lancer le Controller du jeu" dans l'interface Main Controller
```

### Détail étape par étape

**Terminal 1 — Logger :**
```bash
cd VR_Project
python logger.py
```
Sortie attendue :
```
✅ Connecté au broker MQTT !
📡 En écoute sur : #
```

**Terminal 2 — Main Controller :**
```bash
python main_controller.py
```
Sortie attendue :
```
✅ Connecté au broker MQTT !
🌐 Interface disponible sur : http://localhost:7860
```
Ouvrir http://localhost:7860 dans un navigateur.

**Unity :**
- Ouvrir le projet souhaité (boules ou obstacles)
- Appuyer sur **▶️ Play**
- Unity envoie automatiquement sa configuration au Main Controller
- Dans l'interface web, cliquer **"Lancer le Controller du jeu"**
- Le controller spécifique est disponible sur http://localhost:7861

---

## Jeu des boules

### Principe
Des sphères apparaissent disposées en cercle. Le joueur doit cliquer sur chacune d'elles (elles deviennent vertes). Quand toutes sont cliquées, un nouveau cercle apparaît.

### Paramètres contrôlables via le Controller
| Paramètre | Description | Plage |
|-----------|-------------|-------|
| `taille` | Taille des boules | 0.5 à 3.0 |
| `nombre` | Nombre de boules dans le cercle | 2 à 20 |
| `rayon_cercle` | Rayon du cercle | 1.0 à 10.0 |

### Événements publiés sur MQTT
| Événement | Description |
|-----------|-------------|
| `boule_cliquee` | Une boule a été cliquée (avec `boule_id`) |
| `round_termine` | Toutes les boules ont été cliquées (avec `nb_boules`, `duree_secondes`) |

### Configuration Unity (CircleManager.cs)
```csharp
MQTTPublisher.Instance.UserId = "joueur_1";           // Identifiant du joueur
MQTTPublisher.Instance.Topic  = "jeu/boules/evenement"; // Topic de publication
MQTTReceiver.Instance.Topic   = "unity/commands";       // Topic d'écoute
```

---

## Jeu d'obstacles

### Principe
Le joueur se déplace en X/Z pour esquiver des obstacles qui arrivent. En cas de collision, c'est Game Over. Le score augmente à chaque obstacle évité.

### Paramètres contrôlables via le Controller
| Paramètre | Description | Plage |
|-----------|-------------|-------|
| `vitesse` | Vitesse des obstacles | 1.0 à 20.0 |
| `intervalle` | Temps entre deux spawns (secondes) | 0.2 à 5.0 |
| `points` | Points par obstacle évité | 1 à 100 |

### Événements publiés sur MQTT
| Événement | Description |
|-----------|-------------|
| `collision` | Le joueur a touché un obstacle |
| `game_over` | Fin de partie (avec `score_final`) |
| `score_update` | Mise à jour du score (avec `score`) |

### Configuration Unity (GameManager.cs)
```csharp
MQTTPublisher.instance.UserId = "joueur_1";
MQTTPublisher.instance.Topic  = "jeu/obstacle/evenement";
MQTTReceiver.Instance.Topic   = "unity/obstacle/commands";
```

---

## Logger Python

### Description
Le logger `logger.py` est **générique** : il sauvegarde tous les événements MQTT sans connaître le jeu. Il écoute par défaut sur `#` (tous les topics).

### Utilisation
```bash
# Écouter tous les topics (par défaut)
python logger.py

# Écouter uniquement le jeu des boules
python logger.py --topic "jeu/boules/#"

# Écouter uniquement le jeu d'obstacles
python logger.py --topic "jeu/obstacle/#"

# Mode simulation (sans Unity)
python logger.py --simulate
```

### Format des fichiers de log
Les événements sont sauvegardés dans `logs/<user>.json` :
```json
{
  "user": "joueur_1",
  "fichier": 1,
  "events": [
    {
      "user": "joueur_1",
      "evenement": "boule_cliquee",
      "timestamp": 1776932278.77,
      "boule_id": 3,
      "date": "2026-04-23 10:17:58",
      "_topic": "jeu/boules/evenement"
    }
  ]
}
```

> Chaque fichier contient au maximum **100 événements**. Un nouveau fichier est créé automatiquement (`joueur_1_2.json`, `joueur_1_3.json`...).

---

## Controller Gradio

### Description
Interface web Python/Gradio pour contrôler le jeu en temps réel.

### Utilisation manuelle (sans Main Controller)
```bash
python controller_boules.py
```
Puis ouvrir http://localhost:7861

### Fonctionnalités
- Sliders pour modifier les paramètres du jeu en direct
- Bouton **"Envoyer les paramètres"** pour appliquer les changements
- Section **"Messages reçus de Unity"** pour voir l'activité du jeu
- Bouton **"Rafraîchir"** pour actualiser les messages

---

## Main Controller

### Description
`main_controller.py` génère **automatiquement** le controller Gradio adapté au jeu qui vient de démarrer. Plus besoin de coder un controller manuellement pour chaque nouveau jeu.

### Fonctionnement
1. Unity démarre → envoie sa configuration JSON sur `jeu/config`
2. Main Controller reçoit la config → génère `controller_<jeu>.py`
3. L'interface affiche un bouton **"Lancer le Controller du jeu"**
4. Un clic → le controller généré démarre sur le port 7861

### Interface web (port 7860)
- **Statut** : connexion au broker, config reçue
- **Bouton "Rafraîchir le statut"** : vérifie si Unity a envoyé sa config
- **Bouton "Lancer le Controller du jeu"** : démarre le controller généré

---

## Stress Test

### Description
`unity_stress_test.py` envoie une série de commandes MQTT en rafale pour tester la robustesse du système sous charge. Il mesure les FPS de Unity en temps réel pendant le test.

### Prérequis Unity
Ajouter `UnityStressReporter.cs` (dans le dossier `stress/`) dans la scène Unity :
1. Copier `stress/UnityStressReporter.cs` dans `Assets/script/` du projet
2. Créer un **GameObject vide** → nommer `StressReporter`
3. Attacher le script `UnityStressReporter` au GameObject
4. Lancer le jeu ▶️

### Lancer le stress test

**Jeu des boules :**
```bash
python unity_stress_test.py --config config_boules.json
```

**Jeu d'obstacles :**
```bash
python unity_stress_test.py --config config_obstacles.json
```

### Résultats obtenus

**Jeu des boules :**
```
Commandes OK : 200 | Ko : 0 | Durée : 24.2s
FPS : min=113  max=200  moy=150
Chutes < 30 FPS : 0 fois (0%)
✅ VERDICT : 60+ FPS tout le long — Unity tient parfaitement
```

**Jeu d'obstacles :**
```
Commandes OK : 200 | Ko : 0 | Durée : 21.8s
FPS : min=61.1  max=161.7  moy=106.5
Chutes < 30 FPS : 0 fois (0%)
✅ VERDICT : 60+ FPS tout le long — Unity tient parfaitement
```

### Personnaliser le stress test
Modifier `config_obstacles.json` :
```json
{
  "nom": "Jeu d'obstacles",
  "topic_commands": "unity/obstacle/commands",
  "topic_stress": "jeu/stress/fps",
  "phases": [
    {
      "nom": "Vitesse progressive",
      "commandes": {"vitesse": 3.0, "intervalle": 2.0, "points": 10},
      "nb_commandes": 20,
      "intervalle_secondes": 0.5
    }
  ]
}
```

---

## Utiliser les fichiers MQTT sur un autre projet Unity

Les 4 fichiers dans `MQTTgene/` sont **100% génériques** et fonctionnent avec n'importe quel projet Unity, sans aucune dépendance externe.

### Étapes

**1. Copier le dossier `MQTTgene/` dans `Assets/script/` du nouveau projet**

**2. Dans votre script principal, ajouter ces lignes dans `Start()` :**

```csharp
using System.Collections.Generic;
using UnityEngine;

public class MonGameManager : MonoBehaviour
{
    void Start()
    {
        // ── Configurer le Publisher ──────────────────────────────
        MQTTPublisher.Instance.UserId = "joueur_1";
        MQTTPublisher.Instance.Topic  = "jeu/MON_JEU/evenement"; // ← changer
        MQTTPublisher.Instance.Logger = msg => Debug.Log(msg);
        MQTTPublisher.Instance.Start();

        // ── Configurer le Receiver ───────────────────────────────
        MQTTReceiver.Instance.Topic  = "unity/MON_JEU/commands"; // ← changer
        MQTTReceiver.Instance.Logger = msg => Debug.Log(msg);
        MQTTReceiver.Instance.Start();
        MQTTReceiver.OnCommandReceived += OnMqttCommand;
    }

    void OnDestroy()
    {
        MQTTReceiver.OnCommandReceived -= OnMqttCommand;
        MQTTReceiver.Instance.Stop();
        MQTTPublisher.Instance.Stop();
    }

    // ── Thread-safe : dispatch vers le thread principal Unity ────
    private readonly Queue<System.Action> _queue = new Queue<System.Action>();

    void Update()
    {
        while (_queue.Count > 0) _queue.Dequeue()?.Invoke();
    }

    void OnMqttCommand(System.Collections.Generic.Dictionary<string, string> data)
    {
        _queue.Enqueue(() =>
        {
            // Traiter les commandes reçues
            if (data.ContainsKey("ma_commande"))
                Debug.Log("Commande reçue : " + data["ma_commande"]);
        });
    }
}
```

**3. Publier des événements depuis n'importe quel script :**
```csharp
MQTTPublisher.Instance.Publish("mon_evenement", new Dictionary<string, object>
{
    { "valeur", 42 },
    { "info",   "exemple" }
});
// → publie automatiquement avec user + timestamp
```

**4. Lancer le logger pour ce nouveau jeu :**
```bash
python logger.py --topic "jeu/MON_JEU/#"
```

> **Seules 2 lignes changent d'un jeu à l'autre** : les deux topics MQTT.

---

## Résultats obtenus

| Métrique | Valeur |
|----------|--------|
| Stress test broker | 26 153 msg/s, 0 perte sur 1000 messages |
| FPS jeu des boules (stress) | min 113 — max 200 — moy 150 |
| FPS jeu d'obstacles (stress) | min 61 — max 161 — moy 106 |
| Chutes sous 30 FPS | 0 fois (0%) |
| Fichiers MQTT génériques | 4 fichiers C# réutilisables |
| Jeux connectés | 2 (boules + obstacles) |

---

## Fichiers clés

| Fichier | Rôle | Générique ? |
|---------|------|-------------|
| `MQTTClient.cs` | Moteur TCP pur, protocole MQTT 3.1.1 | ✅ Ne change jamais |
| `MQTTPublisher.cs` | Publie les événements Unity | ✅ Changer UserId + Topic |
| `MQTTReceiver.cs` | Reçoit les commandes | ✅ Changer Topic |
| `MQTTController.cs` | Publie ET reçoit (C# pur) | ✅ Changer les topics |
| `logger.py` | Enregistre tous les événements | ✅ Changer `--topic` |
| `main_controller.py` | Génère le controller automatiquement | ✅ Ne change jamais |
| `unity_stress_test.py` | Test de charge Unity | ✅ Changer le config JSON |
| `CircleManager.cs` | Logique jeu des boules | ❌ Spécifique boules |
| `GameManager.cs` | Logique jeu d'obstacles | ❌ Spécifique obstacles |

---

*Projet ESTIA — Brillant Kenet FOUANA — 2026*
