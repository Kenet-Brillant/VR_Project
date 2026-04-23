"""
controller_boules.py
────────────────────
Controller généré automatiquement par main_controller.py
Jeu     : boules
Topic   : unity/commands
"""

import json, time
import gradio as gr
import paho.mqtt.client as mqtt
from datetime import datetime

BROKER_HOST    = "devweb.estia.fr"
BROKER_PORT    = 1883
USERNAME       = "estia"
PASSWORD       = "*aZ9#r8X7"
TOPIC_COMMANDS = "unity/commands"
TOPIC_ECOUTE   = "jeu/boules/evenement"

messages_recus = []

def on_connect_ecoute(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_ECOUTE)
        print(f"✅ Connecté ! En écoute sur : {TOPIC_ECOUTE}")

def on_message_unity(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        event   = payload.get("evenement") or payload.get("event", "?")
        user    = payload.get("user", "?")
        heure   = datetime.now().strftime("%H:%M:%S")
        ligne   = f"[{heure}] {user} — {event}"
        messages_recus.insert(0, ligne)
        if len(messages_recus) > 20:
            messages_recus.pop()
    except Exception as e:
        messages_recus.insert(0, f"[ERREUR] {str(e)}")

import threading
def demarrer_ecoute():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect_ecoute
    client.on_message = on_message_unity
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_forever()

threading.Thread(target=demarrer_ecoute, daemon=True).start()

def publish_command(payload):
    try:
        client = mqtt.Client()
        client.username_pw_set(USERNAME, PASSWORD)
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.publish(TOPIC_COMMANDS, json.dumps(payload))
        client.disconnect()
        return f"✅ Commande envoyée : {json.dumps(payload, ensure_ascii=False)}"
    except Exception as e:
        return f"❌ Erreur : {str(e)}"

def envoyer_parametres(taille, nombre, rayon_cercle):
    payload = {
        "taille": round(float(taille), 2),
        "nombre": round(float(nombre), 2),
        "rayon_cercle": round(float(rayon_cercle), 2),
        "timestamp": time.time()
    }
    return publish_command(payload)

def rafraichir_messages():
    return "\n".join(messages_recus) if messages_recus else "⏳ En attente de messages..."

with gr.Blocks(title="🎮 Controller — boules") as app:
    gr.Markdown("# 🎮 Controller — boules")
    gr.Markdown("Généré automatiquement par le Main Controller.")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### ⚙️ Paramètres")

            taille = gr.Slider(
                minimum=0.5, maximum=3.0,
                value=1.0, step=0.1,
                label="Taille des boules"
            )
            nombre = gr.Slider(
                minimum=2, maximum=20,
                value=8, step=1,
                label="Nombre de boules"
            )
            rayon_cercle = gr.Slider(
                minimum=1.0, maximum=10.0,
                value=3.0, step=0.1,
                label="Rayon du cercle"
            )
        with gr.Column():
            gr.Markdown("### 🚀 Actions")
            btn_envoyer = gr.Button("📤 Envoyer les paramètres", variant="primary")
            statut      = gr.Textbox(label="Statut", interactive=False)
            btn_envoyer.click(
                fn=envoyer_parametres,
                inputs=[taille, nombre, rayon_cercle],
                outputs=statut
            )

    gr.Markdown("---")
    gr.Markdown("### 📨 Messages reçus de Unity")
    messages_box   = gr.Textbox(label="Activité du jeu", lines=10, interactive=False)
    btn_rafraichir = gr.Button("🔄 Rafraîchir")
    btn_rafraichir.click(fn=rafraichir_messages, inputs=[], outputs=messages_box)

if __name__ == "__main__":
    print("🌐 Lancement du Controller boules...")
    app.launch()
