"""
controller.py
-------------
Interface web Gradio pour contrôler le jeu des boules via MQTT.
- Changer la taille des boules
- Changer le nombre de boules
- Changer la taille du cercle (ou aléatoire)
- Régénérer le cercle manuellement

Installation : pip install gradio paho-mqtt
Usage        : python controller.py
"""

import json
import time
import gradio as gr
import paho.mqtt.client as mqtt

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BROKER_HOST    = "devweb.estia.fr"
BROKER_PORT    = 1883
USERNAME       = "estia"
PASSWORD       = "*aZ9#r8X7"
TOPIC_COMMANDS = "unity/commands"
# ──────────────────────────────────────────────────────────────────────────────


# ─── MQTT ─────────────────────────────────────────────────────────────────────

def get_mqtt_client():
    """Crée et connecte un client MQTT."""
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    return client


def publish_command(payload: dict) -> str:
    """Publie une commande MQTT et retourne un message de statut."""
    try:
        client = get_mqtt_client()
        client.publish(TOPIC_COMMANDS, json.dumps(payload))
        client.disconnect()
        print(f"📤 Commande envoyée : {payload}")
        return f"✅ Commande envoyée : {json.dumps(payload, ensure_ascii=False)}"
    except Exception as e:
        return f"❌ Erreur : {str(e)}"


# ─── ACTIONS ──────────────────────────────────────────────────────────────────

def envoyer_parametres(taille_boule, nombre_boules, taille_cercle, cercle_aleatoire):
    """Envoie tous les paramètres en une seule commande."""
    payload = {
        "taille"          : round(float(taille_boule), 2),
        "nombre"          : int(nombre_boules),
        "rayon_cercle"    : -1 if cercle_aleatoire else round(float(taille_cercle), 2),
        "timestamp"       : time.time()
    }
    return publish_command(payload)


def regenerer_cercle():
    """Régénère le cercle sans changer les paramètres."""
    payload = {
        "action"    : "regenerer",
        "timestamp" : time.time()
    }
    return publish_command(payload)


# ─── INTERFACE GRADIO ─────────────────────────────────────────────────────────

def toggle_cercle_slider(aleatoire):
    """Active/désactive le slider de taille du cercle selon la case à cocher."""
    return gr.update(interactive=not aleatoire)


with gr.Blocks(title="🎮 Controller — Jeu des Boules") as app:

    gr.Markdown("# 🎮 Controller — Jeu des Boules")
    gr.Markdown("Modifie les paramètres du jeu et envoie-les à Unity via MQTT.")

    with gr.Row():

        with gr.Column():
            gr.Markdown("### ⚙️ Paramètres")

            taille_boule = gr.Slider(
                minimum=0.5,
                maximum=3.0,
                value=1.0,
                step=0.1,
                label="Taille des boules"
            )

            nombre_boules = gr.Slider(
                minimum=2,
                maximum=20,
                value=8,
                step=1,
                label="Nombre de boules"
            )

            cercle_aleatoire = gr.Checkbox(
                label="Taille du cercle aléatoire",
                value=False
            )

            taille_cercle = gr.Slider(
                minimum=1.0,
                maximum=10.0,
                value=3.0,
                step=0.1,
                label="Taille du cercle (rayon)",
                interactive=True
            )

            # Désactiver le slider si "aléatoire" est coché
            cercle_aleatoire.change(
                fn=toggle_cercle_slider,
                inputs=cercle_aleatoire,
                outputs=taille_cercle
            )

        with gr.Column():
            gr.Markdown("### 🚀 Actions")

            btn_envoyer = gr.Button("📤 Envoyer les paramètres", variant="primary")
            btn_regenerer = gr.Button("🔄 Régénérer le cercle", variant="secondary")

            statut = gr.Textbox(label="Statut", interactive=False)

    btn_envoyer.click(
        fn=envoyer_parametres,
        inputs=[taille_boule, nombre_boules, taille_cercle, cercle_aleatoire],
        outputs=statut
    )

    btn_regenerer.click(
        fn=regenerer_cercle,
        inputs=[],
        outputs=statut
    )


if __name__ == "__main__":
    print("🌐 Lancement du Controller...")
    print(f"🔌 Broker MQTT : {BROKER_HOST}:{BROKER_PORT}")
    app.launch()
