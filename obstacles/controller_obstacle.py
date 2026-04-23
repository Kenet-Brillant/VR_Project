"""
controller_obstacle.py
----------------------
Interface web Gradio pour contrôler le jeu d'obstacles via MQTT.
- Vitesse des obstacles
- Intervalle de spawn
- Points par obstacle évité

Installation : pip install gradio paho-mqtt
Usage        : python controller_obstacle.py
"""

import json
import time
import gradio as gr
import paho.mqtt.client as mqtt

BROKER_HOST    = "devweb.estia.fr"
BROKER_PORT    = 1883
USERNAME       = "estia"
PASSWORD       = "*aZ9#r8X7"
TOPIC_COMMANDS = "unity/obstacle/commands"


def publish_command(payload: dict) -> str:
    try:
        client = mqtt.Client()
        client.username_pw_set(USERNAME, PASSWORD)
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.publish(TOPIC_COMMANDS, json.dumps(payload))
        client.disconnect()
        print(f"📤 Commande envoyée : {payload}")
        return f"✅ Commande envoyée : {json.dumps(payload, ensure_ascii=False)}"
    except Exception as e:
        return f"❌ Erreur : {str(e)}"


def envoyer_parametres(vitesse, intervalle, points):
    payload = {
        "vitesse"    : round(float(vitesse), 1),
        "intervalle" : round(float(intervalle), 1),
        "points"     : int(points),
        "timestamp"  : time.time()
    }
    return publish_command(payload)


with gr.Blocks(title="🎮 Controller — Jeu d'Obstacles") as app:

    gr.Markdown("# 🎮 Controller — Jeu d'Obstacles")
    gr.Markdown("Définit les conditions de départ du jeu et envoie-les à Unity via MQTT.")

    with gr.Row():

        with gr.Column():
            gr.Markdown("### ⚙️ Paramètres")

            vitesse = gr.Slider(
                minimum=1.0,
                maximum=30.0,
                value=5.0,
                step=0.5,
                label="Vitesse des obstacles"
            )

            intervalle = gr.Slider(
                minimum=0.5,
                maximum=10.0,
                value=2.0,
                step=0.5,
                label="Intervalle de spawn (secondes)"
            )

            points = gr.Radio(
                choices=[1, 2, 5, 10],
                value=10,
                label="Points par obstacle évité"
            )

        with gr.Column():
            gr.Markdown("### 🚀 Actions")

            btn_envoyer = gr.Button("📤 Envoyer les paramètres", variant="primary")
            statut      = gr.Textbox(label="Statut", interactive=False)

    btn_envoyer.click(
        fn=envoyer_parametres,
        inputs=[vitesse, intervalle, points],
        outputs=statut
    )


if __name__ == "__main__":
    print("🌐 Lancement du Controller Obstacles...")
    print(f"🔌 Broker MQTT : {BROKER_HOST}:{BROKER_PORT}")
    app.launch()
