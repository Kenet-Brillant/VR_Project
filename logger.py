import json
import os
import time
import argparse
from datetime import datetime
import paho.mqtt.client as mqtt

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BROKER_HOST     = "devweb.estia.fr"
BROKER_PORT     = 1883
USERNAME        = "estia"
PASSWORD        = "*aZ9#r8X7"

DEFAULT_TOPIC   = "#"
LOGS_DIR        = "logs"
MAX_EVENTS      = 100       # Nombre maximum d'événements par fichier


# ─── GESTION DES FICHIERS ─────────────────────────────────────────────────────

def get_log_filepath(user: str, numero: int) -> str:
    """
    Retourne le chemin du fichier log pour un user et un numéro de fichier.
    Exemples :
      numero=1 → logs/joueur_1.json
      numero=2 → logs/joueur_1_2.json
      numero=3 → logs/joueur_1_3.json
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    if numero == 1:
        return os.path.join(LOGS_DIR, f"{user}.json")
    else:
        return os.path.join(LOGS_DIR, f"{user}_{numero}.json")


def get_current_file_number(user: str) -> int:
    """
    Trouve le numéro du fichier actuel pour ce user.
    C'est le dernier fichier qui existe et qui n'a pas encore atteint MAX_EVENTS.
    """
    numero = 1
    while True:
        filepath = get_log_filepath(user, numero)
        if not os.path.exists(filepath):
            # Ce fichier n'existe pas encore — c'est le prochain à créer
            return numero
        # Le fichier existe — vérifie s'il est plein
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = data.get("events", [])
        if len(events) < MAX_EVENTS:
            # Pas encore plein — on utilise celui-ci
            return numero
        # Plein — on passe au suivant
        numero += 1


def load_user_data(user: str, numero: int) -> dict:
    filepath = get_log_filepath(user, numero)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "events" not in data:
            data["events"] = []
        return data
    return {"user": user, "fichier": numero, "events": []}


def save_user_data(user: str, numero: int, data: dict):
    filepath = get_log_filepath(user, numero)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Sauvegardé : {os.path.abspath(filepath)}")


# ─── ENREGISTREMENT D'UN ÉVÉNEMENT ───────────────────────────────────────────

def log_event(topic: str, payload: dict):
    """
    Sauvegarde n'importe quel événement reçu.
    - Si le fichier actuel a atteint 100 événements, un nouveau fichier est créé.
    Convention minimale : le payload doit avoir 'user' et 'timestamp'.
    """
    user = payload.get("user", "inconnu")

    if "date" not in payload:
        payload["date"] = datetime.fromtimestamp(
            payload.get("timestamp", time.time())
        ).strftime("%Y-%m-%d %H:%M:%S")

    payload["_topic"] = topic

    event_type = payload.get("evenement") or payload.get("event", "inconnu")
    print(f"📨 [{user}] {event_type} — topic: {topic}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("-" * 60)

    # Trouve le bon fichier (ou en crée un nouveau si plein)
    numero = get_current_file_number(user)
    data   = load_user_data(user, numero)

    # Vérifie si on vient d'atteindre la limite
    if len(data["events"]) >= MAX_EVENTS:
        numero += 1
        data = load_user_data(user, numero)
        print(f"📁 Fichier plein ! Nouveau fichier : {get_log_filepath(user, numero)}")

    data["events"].append(payload)
    save_user_data(user, numero, data)

    # Informe si on approche de la limite
    nb = len(data["events"])
    if nb == MAX_EVENTS:
        print(f"⚠️  [{user}] Fichier {numero} plein ({MAX_EVENTS} événements). Le prochain événement créera un nouveau fichier.")
    elif nb >= MAX_EVENTS - 10:
        print(f"ℹ️  [{user}] Fichier {numero} : {nb}/{MAX_EVENTS} événements.")


# ─── MQTT ────────────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    topic = userdata["topic"]
    if rc == 0:
        print(f"✅ Connecté au broker MQTT !")
        print(f"📡 En écoute sur : {topic}\n")
        client.subscribe(topic)
    else:
        print(f"❌ Erreur de connexion, code : {rc}")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        log_event(topic, payload)
    except json.JSONDecodeError:
        print(f"⚠️  Message non-JSON sur {topic} : {msg.payload}")


# ─── SIMULATION ──────────────────────────────────────────────────────────────

def simulate(client, topic_base: str):
    """Simule des événements génériques pour tester le Logger."""
    import random
    print("🎮 Mode simulation activé...\n")
    user = "test_user"

    event1 = {
        "user"      : user,
        "evenement" : "action_joueur",
        "details"   : "clic sur objet",
        "objet_id"  : 3,
        "timestamp" : time.time()
    }
    client.publish(f"{topic_base}/evenement", json.dumps(event1))
    print("➡️  Publié : action_joueur")
    time.sleep(1)

    event2 = {
        "user"      : user,
        "evenement" : "score_mis_a_jour",
        "score"     : random.randint(10, 100),
        "timestamp" : time.time()
    }
    client.publish(f"{topic_base}/evenement", json.dumps(event2))
    print("➡️  Publié : score_mis_a_jour")
    time.sleep(1)

    event3 = {
        "user"            : user,
        "evenement"       : "session_terminee",
        "duree_secondes"  : 42.5,
        "timestamp"       : time.time()
    }
    client.publish(f"{topic_base}/evenement", json.dumps(event3))
    print("➡️  Publié : session_terminee")
    print("\n✅ Simulation terminée ! Vérifie logs/test_user.json")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Logger MQTT générique pour Unity")
    parser.add_argument(
        "--topic",
        type=str,
        default=DEFAULT_TOPIC,
        help=f"Topic MQTT à écouter (défaut: '{DEFAULT_TOPIC}')"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Envoie des événements fictifs pour tester"
    )
    args = parser.parse_args()

    topic = args.topic

    client = mqtt.Client(userdata={"topic": topic})
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"🔌 Connexion à {BROKER_HOST}:{BROKER_PORT}...")
    print(f"📋 Limite : {MAX_EVENTS} événements par fichier\n")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    if args.simulate:
        topic_base = topic.rstrip("/#") or "jeu/test"
        client.loop_start()
        time.sleep(1)
        simulate(client, topic_base)
        time.sleep(2)
        client.loop_stop()
    else:
        client.loop_forever()


if __name__ == "__main__":
    main()