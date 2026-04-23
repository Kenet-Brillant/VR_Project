# Intégrer MQTT dans votre projet Unity

Ce guide vous explique comment connecter votre jeu Unity à une infrastructure MQTT pour :
- **Enregistrer** automatiquement tout ce qui se passe dans le jeu (clics, scores, événements...)
- **Contrôler** les paramètres du jeu à distance depuis une interface web

> 💡 Vous n'avez pas besoin de comprendre comment MQTT fonctionne en interne. Suivez simplement les étapes dans l'ordre.

---

## Ce dont vous avez besoin

### Installer les bibliothèques Python
Ouvrez un terminal et tapez :
```bash
pip install paho-mqtt gradio
```

### Informations du broker MQTT
Le broker est le "serveur intermédiaire" par lequel tous les messages transitent.
```
Host     : devweb.estia.fr
Port     : 1883
Username : estia
Password : *aZ9#r8X7
```

---

## Étape 1 — Copier les fichiers C# dans votre projet Unity

Dans ce dépôt, vous trouverez un dossier `MQTTgene/`. Copiez-le dans `Assets/script/` de votre projet Unity.

```
Assets/script/MQTTgene/
├── MQTTClient.cs       ← le moteur qui gère la connexion réseau. Ne jamais modifier.
├── MQTTPublisher.cs    ← sert à ENVOYER des messages depuis Unity vers le broker
├── MQTTReceiver.cs     ← sert à RECEVOIR des commandes depuis le broker vers Unity
└── MQTTController.cs   ← combine les deux (optionnel, utile hors Unity)
```

> ✅ Ces fichiers n'ont aucune dépendance externe. Aucun package Unity à installer.  
> ✅ Compatibles avec toutes les versions de Unity.

---

## Étape 2 — Connecter MQTT à votre script principal

### Qu'est-ce que le "script principal" ?

C'est le script C# qui gère la logique centrale de votre jeu. Dans le jeu des boules c'est `CircleManager.cs`, dans le jeu d'obstacles c'est `GameManager.cs`. Dans votre jeu, ce sera le script qui tourne depuis le début de la partie — peu importe son nom.

### Ce que vous devez ajouter dans ce script

Vous allez modifier **quatre endroits** dans votre script existant.

---

### 2a — Ajouter une Queue en haut de la classe

```csharp
private readonly Queue<System.Action> _queue = new Queue<System.Action>();
```

**Pourquoi cette ligne ?**  
MQTT reçoit les messages sur un "thread secondaire" (un processus parallèle). Unity n'autorise pas à modifier des objets du jeu depuis un thread secondaire — sinon le jeu plante. La Queue sert de "boîte intermédiaire" : les messages y arrivent, et Unity les traite au bon moment dans `Update()`.

**Copiez cette ligne telle quelle, sans la modifier.**

---

### 2b — Démarrer MQTT dans le Start()

Ajoutez ces lignes dans le `Start()` de votre script. C'est ici que vous configurez la connexion.

Dans le jeu des boules, voici exactement ce qu'on a écrit :

```csharp
void Start()
{
    // ────────────────────────────────────────────────────────────────────
    // PUBLISHER — Unity envoie des messages vers le broker
    // ────────────────────────────────────────────────────────────────────
    MQTTPublisher.Instance.UserId = "joueur_1";
    //  ^ L'identifiant du joueur. Ce nom apparaîtra dans les fichiers de log.
    //    Changez-le si vous souhaitez identifier plusieurs joueurs.

    MQTTPublisher.Instance.Topic  = "jeu/boules/evenement";
    //  ^ L'adresse sur laquelle Unity publie ses messages.
    //    Pour votre jeu, remplacez "boules" par le nom de votre jeu.
    //    Exemple pour le jeu d'obstacles : "jeu/obstacle/evenement"

    MQTTPublisher.Instance.Logger = msg => Debug.Log(msg);
    //  ^ Affiche les messages MQTT dans la Console Unity. Utile pour vérifier
    //    que les messages partent bien.

    MQTTPublisher.Instance.Start();
    //  ^ Lance la connexion au broker. À appeler en dernier pour le Publisher.


    // ────────────────────────────────────────────────────────────────────
    // RECEIVER — Unity reçoit des commandes depuis le controller web
    // ────────────────────────────────────────────────────────────────────
    MQTTReceiver.Instance.Topic  = "unity/commands";
    //  ^ L'adresse sur laquelle Unity écoute les commandes du controller.
    //    Pour votre jeu, adaptez ce topic.
    //    Exemple pour le jeu d'obstacles : "unity/obstacle/commands"

    MQTTReceiver.Instance.Logger = msg => Debug.Log(msg);
    MQTTReceiver.Instance.Start();
    MQTTReceiver.OnCommandReceived += OnMqttCommand;
    //  ^ Quand une commande arrive, Unity appelle automatiquement
    //    la fonction OnMqttCommand() que vous allez créer à l'étape 2d.


    // ────────────────────────────────────────────────────────────────────
    // CONFIG — Envoie la description du jeu au Main Controller
    // ────────────────────────────────────────────────────────────────────
    EnvoyerConfig();
    //  ^ Envoie au Main Controller la liste des paramètres que votre jeu
    //    accepte. Le Main Controller génère ensuite automatiquement
    //    l'interface web avec les bons sliders. Voir Étape 4.
}
```

---

### 2c — Arrêter MQTT proprement dans OnDestroy()

Ajoutez cette fonction dans votre script. Elle s'exécute automatiquement quand Unity ferme la scène :

```csharp
void OnDestroy()
{
    MQTTReceiver.OnCommandReceived -= OnMqttCommand;
    MQTTReceiver.Instance.Stop();
    MQTTPublisher.Instance.Stop();
}
```

**Pourquoi ?**  
Sans cette fonction, la connexion MQTT reste ouverte en arrière-plan après la fermeture du jeu, ce qui peut causer des comportements inattendus si vous relancez Unity.

---

### 2d — Traiter les commandes reçues

Ajoutez ces deux fonctions dans votre script :

```csharp
// Cette fonction tourne à chaque frame. Elle vide la Queue et applique
// les changements dans Unity. Copiez-la telle quelle sans la modifier.
void Update()
{
    while (_queue.Count > 0)
        _queue.Dequeue()?.Invoke();
}


// Cette fonction est appelée automatiquement quand le Controller
// envoie une commande vers Unity.
// C'est ICI que vous adaptez le code à votre jeu.
void OnMqttCommand(Dictionary<string, string> data)
{
    _queue.Enqueue(() =>
    {
        // Exemple tiré du jeu des boules :
        // Le controller envoie "taille", "nombre" et "rayon_cercle"
        // Unity les reçoit ici et met à jour le jeu.

        if (data.ContainsKey("taille"))
        {
            float taille = float.Parse(data["taille"],
                System.Globalization.CultureInfo.InvariantCulture);
            // Applique la nouvelle taille des boules
            sphereRadius = taille;
        }

        if (data.ContainsKey("nombre"))
        {
            int nombre = (int)float.Parse(data["nombre"],
                System.Globalization.CultureInfo.InvariantCulture);
            // Met à jour le nombre de boules dans le cercle
            numberOfSpheres = nombre;
        }

        if (data.ContainsKey("rayon_cercle"))
        {
            float rayon = float.Parse(data["rayon_cercle"],
                System.Globalization.CultureInfo.InvariantCulture);
            forcedRadius = rayon;
        }

        // Autre exemple tiré du jeu d'obstacles :
        // if (data.ContainsKey("vitesse"))
        //     obstacleSpeed = float.Parse(data["vitesse"], ...);
        //
        // if (data.ContainsKey("intervalle"))
        //     spawnInterval = float.Parse(data["intervalle"], ...);

        // Une fois les paramètres mis à jour, on régénère le jeu
        Regenerate();
    });
}
```

**En résumé :** dans `OnMqttCommand()`, listez tous les paramètres que votre jeu peut recevoir depuis le controller web, et décrivez ce qu'il faut faire quand chacun arrive. Adaptez les noms des clés (`taille`, `nombre`, `vitesse`...) aux paramètres réels de votre jeu.

---

## Étape 3 — Publier des événements depuis votre jeu

Un "événement" c'est n'importe quoi qui se passe dans votre jeu et que vous souhaitez enregistrer.

Pour publier un événement, appelez cette ligne depuis **n'importe quel script** de votre jeu :

```csharp
// Exemple 1 — tiré du jeu des boules
// Publié depuis SphereClick.cs quand le joueur clique sur une boule
MQTTPublisher.Instance.Publish("boule_cliquee", new Dictionary<string, object>
{
    { "boule_id", bouleId }
});

// Exemple 2 — tiré du jeu des boules
// Publié depuis CircleManager.cs quand toutes les boules sont cliquées
MQTTPublisher.Instance.Publish("round_termine", new Dictionary<string, object>
{
    { "nb_boules",       numberOfSpheres },
    { "nouveau_rayon",   circleRadius    },
    { "duree_secondes",  duree           }
});

// Exemple 3 — tiré du jeu d'obstacles
// Publié depuis GameManager.cs quand c'est Game Over
MQTTPublisher.Instance.Publish("game_over", new Dictionary<string, object>
{
    { "score_final", score }
});

// Exemple 4 — tiré du jeu d'obstacles
// Publié depuis PlayerController.cs quand le joueur touche un obstacle
MQTTPublisher.Instance.Publish("collision", new Dictionary<string, object>
{
    { "obstacle_tag", collision.gameObject.tag }
});
```

**Ce que le broker reçoit concrètement pour l'exemple 2 :**
```json
{
    "user":           "joueur_1",
    "evenement":      "round_termine",
    "timestamp":      1776932278.77,
    "nb_boules":      8,
    "nouveau_rayon":  3.5,
    "duree_secondes": 12.4
}
```

> 💡 Le `user` et le `timestamp` sont ajoutés **automatiquement** par `MQTTPublisher`. Vous n'avez pas à les écrire.

---

## Étape 4 — Décrire les paramètres de votre jeu

Cette fonction permet au Main Controller de générer automatiquement l'interface web avec les bons sliders pour **votre** jeu. Ajoutez-la dans votre script et appelez-la à la fin du `Start()`.

**Exemple tiré du jeu des boules :**

```csharp
void EnvoyerConfig()
{
    // Décrivez ici les paramètres que votre jeu accepte depuis le controller.
    // Chaque paramètre deviendra un slider dans l'interface web.
    //
    // Pour chaque paramètre, précisez :
    //   "nom"     : le nom de la clé que vous lisez dans OnMqttCommand()
    //   "label"   : le texte affiché dans l'interface web
    //   "type"    : "slider" pour un nombre
    //   "min/max" : les valeurs minimum et maximum
    //   "default" : la valeur par défaut au démarrage
    //   "step"    : le pas du slider (0.1, 0.5, 1...)

    string json =
        "{\"jeu\": \"boules\"," +
        "\"topic_events\": \"jeu/boules/evenement\"," +
        "\"topic_commands\": \"unity/commands\"," +
        "\"commandes\": [" +

            "{\"nom\": \"taille\"," +
            " \"label\": \"Taille des boules\"," +
            " \"type\": \"slider\"," +
            " \"min\": 0.5, \"max\": 3.0, \"default\": 1.0, \"step\": 0.1}," +

            "{\"nom\": \"nombre\"," +
            " \"label\": \"Nombre de boules\"," +
            " \"type\": \"slider\"," +
            " \"min\": 2, \"max\": 20, \"default\": 8, \"step\": 1}," +

            "{\"nom\": \"rayon_cercle\"," +
            " \"label\": \"Rayon du cercle\"," +
            " \"type\": \"slider\"," +
            " \"min\": 1.0, \"max\": 10.0, \"default\": 3.0, \"step\": 0.1}" +

        "]}";

    MQTTPublisher.Instance.PublishRaw("jeu/config", json);
    Debug.Log("Config envoyée au Main Controller !");
}
```

**Exemple tiré du jeu d'obstacles (pour comparaison) :**

```csharp
// Les paramètres changent, mais la structure reste exactement la même.
"{\"nom\": \"vitesse\",    \"label\": \"Vitesse des obstacles\", ...}," +
"{\"nom\": \"intervalle\", \"label\": \"Intervalle de spawn\",   ...}," +
"{\"nom\": \"points\",     \"label\": \"Points par esquive\",    ...}"
```

> 💡 Ajoutez autant de paramètres que vous voulez. Chacun deviendra un slider dans l'interface web.

---

## Étape 5 — Lancer le système

### Ordre de démarrage — à respecter impérativement

```
1. Terminal 1 :  python logger.py
2. Terminal 2 :  python main_controller.py
3. Unity       :  ▶️ Play
```

Ne lancez pas Unity en premier. Le logger et le main controller doivent être connectés au broker avant que Unity démarre et envoie sa config.

### Terminal 1 — Lancer le logger

```bash
python logger.py
```

Sortie attendue :
```
✅ Connecté au broker MQTT !
📡 En écoute sur : #
```

Dès que Unity publie un événement, le logger le reçoit et le sauvegarde automatiquement dans `logs/joueur_1.json`. Chaque fichier contient au maximum 100 événements — un nouveau fichier est créé ensuite (`joueur_1_2.json`, etc.).

Pour ne logger que votre jeu :
```bash
python logger.py --topic "jeu/boules/#"
# ou
python logger.py --topic "jeu/obstacle/#"
```

### Terminal 2 — Lancer le Main Controller

```bash
python main_controller.py
```

Ouvrez **http://localhost:7860** dans votre navigateur.

Quand Unity démarre et envoie sa config, le Main Controller génère automatiquement le controller de votre jeu. Cliquez sur **"Lancer le Controller du jeu"** — l'interface avec vos sliders est disponible sur **http://localhost:7861**.

---

## Résumé — Ce qui change pour chaque nouveau jeu

Vous n'avez que **4 choses à adapter** — tout le reste est identique :

| Ce qu'on change | Où | Exemple boules | Exemple obstacles |
|---|---|---|---|
| Topic Publisher | `Start()` | `"jeu/boules/evenement"` | `"jeu/obstacle/evenement"` |
| Topic Receiver | `Start()` | `"unity/commands"` | `"unity/obstacle/commands"` |
| Paramètres reçus | `OnMqttCommand()` | `taille`, `nombre`, `rayon_cercle` | `vitesse`, `intervalle`, `points` |
| Config envoyée | `EnvoyerConfig()` | 3 sliders boules | 3 sliders obstacles |

> Les fichiers `MQTTClient.cs`, `MQTTPublisher.cs`, `MQTTReceiver.cs`, `logger.py` et `main_controller.py` **ne changent jamais**, quel que soit le jeu.

---

*Projet ESTIA — Brillant Kenet FOUANA — 2026*
