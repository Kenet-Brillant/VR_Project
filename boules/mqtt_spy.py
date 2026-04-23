"""
mqtt_spy.py
-----------
Écoute TOUS les messages MQTT et les affiche proprement.
Lance ce script pendant que tu joues dans Unity pour voir
exactement ce qu'il envoie.

Installation : pip install paho-mqtt
Usage        : python mqtt_spy.py
"""

import json
from datetime import datetime
import paho.mqtt.client as mqtt

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BROKER_HOST = "devweb.estia.fr"
BROKER_PORT = 1883
USERNAME    = "estia"
PASSWORD    = "*aZ9#r8X7"
# ──────────────────────────────────────────────────────────────────────────────


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connecté au broker MQTT !")
        print("📡 En écoute sur TOUS les topics (#)...\n")
        client.subscribe("#")   # # = wildcard → tous les topics
    else:
        print(f"❌ Erreur de connexion, code : {rc}")


def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    topic     = msg.topic
    payload   = msg.payload.decode("utf-8", errors="replace")

    # On essaie de parser en JSON pour un affichage plus lisible
    try:
        data = json.loads(payload)
        payload_display = json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        payload_display = payload   # texte brut si pas du JSON

    print(f"[{timestamp}] 📨 TOPIC : {topic}")
    print(f"{payload_display}")
    print("-" * 60)


client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

print(f"🔌 Connexion à {BROKER_HOST}:{BROKER_PORT}...")
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()
