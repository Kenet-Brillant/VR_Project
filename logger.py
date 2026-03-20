"""
logger.py
---------
Logger MQTT pour le jeu des boules.
- Écoute les messages MQTT du jeu
- Accumule les clics du round en cours
- Génère un résumé complet à la fin de chaque round dans logs/<user>.json

Installation : pip install paho-mqtt
Usage        : python logger.py

Pour tester sans Unity :
             python logger.py --simulate
"""

import json
import os
import time
import argparse
import random
from datetime import datetime
import paho.mqtt.client as mqtt

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BROKER_HOST = "devweb.estia.fr"
BROKER_PORT = 1883
USERNAME    = "estia"
PASSWORD    = "*aZ9#r8X7"

TOPIC_JEU   = "jeu/boules/#"
LOGS_DIR    = "logs"
# ──────────────────────────────────────────────────────────────────────────────

# ─── ÉTAT EN MÉMOIRE ──────────────────────────────────────────────────────────
clics_en_cours = {}
# ──────────────────────────────────────────────────────────────────────────────


# ─── UTILITAIRES ──────────────────────────────────────────────────────────────

def get_log_filepath(user: str) -> str:
    os.makedirs(LOGS_DIR, exist_ok=True)
    return os.path.join(LOGS_DIR, f"{user}.json")


def load_user_data(user: str) -> dict:
    filepath = get_log_filepath(user)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "rounds" not in data:
            data["rounds"] = []
        return data
    return {"user": user, "rounds": []}


def save_user_data(user: str, data: dict):
    filepath = get_log_filepath(user)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Fichier sauvegardé : {os.path.abspath(filepath)}")


# ─── TRAITEMENT DES ÉVÉNEMENTS ────────────────────────────────────────────────

def traiter_boule_cliquee(payload: dict):
    user     = payload.get("user", "inconnu")
    boule_id = payload.get("boule_id", -1)
    ts       = payload.get("timestamp", time.time())

    if user not in clics_en_cours:
        clics_en_cours[user] = []

    clics_en_cours[user].append({"boule_id": boule_id, "timestamp": ts})
    print(f"🖱️  [{user}] Boule {boule_id} cliquée ({len(clics_en_cours[user])} clic(s) ce round)")


def traiter_round_termine(payload: dict):
    user         = payload.get("user", "inconnu")
    nb_boules    = payload.get("nb_boules", 0)
    rayon        = round(payload.get("nouveau_rayon", 0), 3)
    duree        = round(payload.get("duree_secondes", 0), 3)
    ts           = payload.get("timestamp", time.time())
    date_lisible = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    # Charger les données existantes pour calculer le numéro du round
    data = load_user_data(user)
    round_numero = len(data["rounds"]) + 1

    # Structure plate — même disposition que l'ancienne version
    round_data = {
        "user"          : user,
        "evenement"     : "round_termine",
        "round_numero"  : round_numero,
        "nb_boules"     : nb_boules,
        "nouveau_rayon" : rayon,
        "duree_secondes": duree,
        "timestamp"     : ts,
        "date"          : date_lisible
    }

    data["rounds"].append(round_data)
    save_user_data(user, data)

    # Réinitialiser les clics en mémoire pour ce joueur
    clics_en_cours[user] = []

    print(f"🏁 [{user}] Round {round_numero} terminé !")
    print(json.dumps(round_data, indent=2, ensure_ascii=False))
    print("-" * 60)


def log_event(payload: dict):
    event_type = payload.get("event") or payload.get("evenement", "inconnu")

    if event_type == "boule_cliquee":
        traiter_boule_cliquee(payload)
    elif event_type == "round_termine":
        traiter_round_termine(payload)
    else:
        print(f"⚠️  Événement inconnu : {event_type}")


# ─── MQTT ─────────────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connecté au broker MQTT !")
        print(f"📡 En écoute sur le topic : {TOPIC_JEU}\n")
        client.subscribe(TOPIC_JEU)
    else:
        print(f"❌ Erreur de connexion, code : {rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        log_event(payload)
    except json.JSONDecodeError:
        print(f"⚠️  Message non-JSON reçu sur {msg.topic} : {msg.payload}")


# ─── MODE SIMULATION ──────────────────────────────────────────────────────────

def simulate(client):
    print("🎮 Mode simulation activé — envoi de données fictives...\n")
    user      = "test_user"
    nb_boules = 6

    for boule_id in range(1, nb_boules + 1):
        event = {
            "user"      : user,
            "event"     : "boule_cliquee",
            "boule_id"  : boule_id,
            "timestamp" : time.time()
        }
        client.publish("jeu/boules/evenement", json.dumps(event))
        print(f"➡️  Publié : boule_cliquee (boule {boule_id})")
        time.sleep(1.5)

    event_fin = {
        "user"            : user,
        "event"           : "round_termine",
        "nb_boules"       : nb_boules,
        "nouveau_rayon"   : round(random.uniform(1.5, 4.0), 2),
        "duree_secondes"  : round(nb_boules * 1.5, 1),
        "timestamp"       : time.time()
    }
    client.publish("jeu/boules/evenement", json.dumps(event_fin))
    print("➡️  Publié : round_termine")
    print("\n✅ Simulation terminée ! Vérifie le fichier logs/test_user.json")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Envoie des données fictives pour tester le Logger"
    )
    args = parser.parse_args()

    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"🔌 Connexion à {BROKER_HOST}:{BROKER_PORT}...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    if args.simulate:
        client.loop_start()
        time.sleep(1)
        simulate(client)
        time.sleep(2)
        client.loop_stop()
    else:
        client.loop_forever()


if __name__ == "__main__":
    main()
