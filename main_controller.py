"""
main_controller.py
------------------
Main Controller Gradio — génère automatiquement un controller
adapté à n'importe quel jeu Unity.

Fonctionnement :
  1. Unity démarre et envoie sa config via MQTT
  2. Le Main Controller reçoit la config et génère controller_<jeu>.py
  3. L'interface Gradio affiche les bons sliders automatiquement
  4. Tu envoies des commandes et vois les events de Unity

Installation : pip install gradio paho-mqtt
Usage        : python main_controller.py
"""

import json
import time
import os
import threading
import subprocess
import gradio as gr
import paho.mqtt.client as mqtt
from datetime import datetime

# ─── CONFIG MQTT ──────────────────────────────────────────────────────────────
BROKER_HOST    = "devweb.estia.fr"
BROKER_PORT    = 1883
USERNAME       = "estia"
PASSWORD       = "*aZ9#r8X7"
TOPIC_CONFIG   = "jeu/config"   # topic sur lequel Unity envoie sa config
# ──────────────────────────────────────────────────────────────────────────────

# ─── ÉTAT GLOBAL ──────────────────────────────────────────────────────────────
config_recue      = None    # config JSON reçue de Unity
messages_recus    = []      # messages reçus de Unity
client_ecoute     = None    # client MQTT en écoute
MAX_MESSAGES      = 20
# ──────────────────────────────────────────────────────────────────────────────


# ─── ÉCOUTE MQTT ──────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_CONFIG)
        client.subscribe("#")   # écoute tout pour les events Unity
        print(f"✅ Main Controller connecté au broker")
        print(f"📡 En attente de config Unity sur : {TOPIC_CONFIG}")
    else:
        print(f"❌ Erreur connexion : {rc}")


def on_message(client, userdata, msg):
    global config_recue
    try:
        payload = json.loads(msg.payload.decode("utf-8"))

        # Config envoyée par Unity au démarrage
        if msg.topic == TOPIC_CONFIG:
            config_recue = payload
            print(f"🎮 Config reçue du jeu : {payload.get('jeu', '?')}")
            # Génère automatiquement le controller
            write_controller(payload)
            return

        # Events envoyés par Unity pendant le jeu
        topic_events = config_recue.get("topic_events", "") if config_recue else ""
        if topic_events and msg.topic.startswith(topic_events.rstrip("#").rstrip("/")):
            event  = payload.get("evenement") or payload.get("event", "?")
            user   = payload.get("user", "?")
            heure  = datetime.now().strftime("%H:%M:%S")

            if event == "boule_cliquee":
                ligne = f"[{heure}] 🖱️  {user} — boule {payload.get('boule_id', '?')} cliquée"
            elif event == "round_termine":
                duree = round(payload.get("duree_secondes", 0), 1)
                rayon = round(payload.get("nouveau_rayon", 0), 2)
                nb    = payload.get("nb_boules", "?")
                ligne = f"[{heure}] ✅ {user} — round terminé | {nb} boules | {duree}s | rayon {rayon}"
            else:
                ligne = f"[{heure}] 📨 {user} — {event}"

            messages_recus.insert(0, ligne)
            if len(messages_recus) > MAX_MESSAGES:
                messages_recus.pop()

    except Exception as e:
        print(f"❌ Erreur message : {e}")


def demarrer_ecoute():
    global client_ecoute
    client_ecoute = mqtt.Client()
    client_ecoute.username_pw_set(USERNAME, PASSWORD)
    client_ecoute.on_connect = on_connect
    client_ecoute.on_message = on_message
    client_ecoute.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client_ecoute.loop_forever()


# Lance l'écoute dans un thread de fond
thread = threading.Thread(target=demarrer_ecoute, daemon=True)
thread.start()


# ─── WRITE.PY — Génération automatique du controller ─────────────────────────

def write_controller(config: dict) -> str:
    """
    Génère automatiquement un fichier controller_<jeu>.py
    à partir de la config reçue de Unity.
    """
    jeu             = config.get("jeu", "generic")
    topic_commands  = config.get("topic_commands", f"unity/{jeu}/commands")
    topic_events    = config.get("topic_events",   f"jeu/{jeu}/#")
    commandes       = config.get("commandes", [])

    filename = f"controller_{jeu}.py"

    # Génère les sliders Gradio selon les commandes définies dans la config
    sliders_code   = ""
    inputs_list    = []
    payload_lines  = ""

    for cmd in commandes:
        nom     = cmd.get("nom")
        label   = cmd.get("label", nom)
        type_   = cmd.get("type", "slider")
        default = cmd.get("default", 1)

        var_name = nom.replace("-", "_").replace(" ", "_")
        inputs_list.append(var_name)

        if type_ == "slider":
            min_v = cmd.get("min", 0)
            max_v = cmd.get("max", 10)
            step  = cmd.get("step", 0.1)
            sliders_code += f"""
            {var_name} = gr.Slider(
                minimum={min_v}, maximum={max_v},
                value={default}, step={step},
                label="{label}"
            )"""
            payload_lines += f'        "{nom}": round(float({var_name}), 2),\n'

        elif type_ == "radio":
            choices = cmd.get("choices", [1, 2, 5])
            sliders_code += f"""
            {var_name} = gr.Radio(
                choices={choices},
                value={default},
                label="{label}"
            )"""
            payload_lines += f'        "{nom}": int({var_name}),\n'

        elif type_ == "checkbox":
            sliders_code += f"""
            {var_name} = gr.Checkbox(
                value={str(default)},
                label="{label}"
            )"""
            payload_lines += f'        "{nom}": bool({var_name}),\n'

    inputs_str = ", ".join(inputs_list)
    fn_args    = ", ".join(inputs_list)

    # Contenu du fichier généré
    code = f'''"""
{filename}
{"─" * len(filename)}
Controller généré automatiquement par main_controller.py
Jeu     : {jeu}
Topic   : {topic_commands}
"""

import json, time
import gradio as gr
import paho.mqtt.client as mqtt
from datetime import datetime

BROKER_HOST    = "{BROKER_HOST}"
BROKER_PORT    = {BROKER_PORT}
USERNAME       = "{USERNAME}"
PASSWORD       = "{PASSWORD}"
TOPIC_COMMANDS = "{topic_commands}"
TOPIC_ECOUTE   = "{topic_events}"

messages_recus = []

def on_connect_ecoute(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_ECOUTE)
        print(f"✅ Connecté ! En écoute sur : {{TOPIC_ECOUTE}}")

def on_message_unity(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        event   = payload.get("evenement") or payload.get("event", "?")
        user    = payload.get("user", "?")
        heure   = datetime.now().strftime("%H:%M:%S")
        ligne   = f"[{{heure}}] {{user}} — {{event}}"
        messages_recus.insert(0, ligne)
        if len(messages_recus) > 20:
            messages_recus.pop()
    except Exception as e:
        messages_recus.insert(0, f"[ERREUR] {{str(e)}}")

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
        return f"✅ Commande envoyée : {{json.dumps(payload, ensure_ascii=False)}}"
    except Exception as e:
        return f"❌ Erreur : {{str(e)}}"

def envoyer_parametres({fn_args}):
    payload = {{
{payload_lines}        "timestamp": time.time()
    }}
    return publish_command(payload)

def rafraichir_messages():
    return "\\n".join(messages_recus) if messages_recus else "⏳ En attente de messages..."

with gr.Blocks(title="🎮 Controller — {jeu}") as app:
    gr.Markdown("# 🎮 Controller — {jeu}")
    gr.Markdown("Généré automatiquement par le Main Controller.")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### ⚙️ Paramètres")
{sliders_code}
        with gr.Column():
            gr.Markdown("### 🚀 Actions")
            btn_envoyer = gr.Button("📤 Envoyer les paramètres", variant="primary")
            statut      = gr.Textbox(label="Statut", interactive=False)
            btn_envoyer.click(
                fn=envoyer_parametres,
                inputs=[{inputs_str}],
                outputs=statut
            )

    gr.Markdown("---")
    gr.Markdown("### 📨 Messages reçus de Unity")
    messages_box   = gr.Textbox(label="Activité du jeu", lines=10, interactive=False)
    btn_rafraichir = gr.Button("🔄 Rafraîchir")
    btn_rafraichir.click(fn=rafraichir_messages, inputs=[], outputs=messages_box)

if __name__ == "__main__":
    print("🌐 Lancement du Controller {jeu}...")
    app.launch()
'''

    # Sauvegarde le fichier généré
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"✅ Controller généré : {filename}")
    return filename


# ─── ENVOI DE COMMANDES ───────────────────────────────────────────────────────

def publish_command(topic: str, payload: dict) -> str:
    try:
        client = mqtt.Client()
        client.username_pw_set(USERNAME, PASSWORD)
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.publish(topic, json.dumps(payload))
        client.disconnect()
        return f"✅ Commande envoyée : {json.dumps(payload, ensure_ascii=False)}"
    except Exception as e:
        return f"❌ Erreur : {str(e)}"


# ─── INTERFACE GRADIO PRINCIPALE ──────────────────────────────────────────────

def get_statut_config():
    if config_recue:
        jeu      = config_recue.get("jeu", "?")
        nb_cmds  = len(config_recue.get("commandes", []))
        filename = f"controller_{jeu}.py"
        existe   = "✅ Généré" if os.path.exists(filename) else "⏳ En cours..."
        return (
            f"✅ Config reçue du jeu : **{jeu}**\n"
            f"📋 Commandes disponibles : {nb_cmds}\n"
            f"📄 Fichier : {filename} — {existe}"
        )
    return "⏳ En attente de la config Unity..."


def lancer_controller():
    if not config_recue:
        return "❌ Aucune config reçue — lance Unity d'abord !", ""
    jeu      = config_recue.get("jeu", "generic")
    filename = f"controller_{jeu}.py"
    if not os.path.exists(filename):
        return f"❌ Fichier {filename} introuvable — relance Unity.", ""
    subprocess.Popen(["python", filename])
    url = "http://127.0.0.1:7861"
    lien = f'''<a href="{url}" target="_blank"
        style="display:inline-block; margin-top:10px; padding:12px 24px;
               background:#f97316; color:white; font-weight:bold;
               border-radius:8px; text-decoration:none; font-size:16px;">
        🎮 Ouvrir le Controller du jeu →
    </a>'''
    return f"🚀 Controller lancé sur {url}", lien


def rafraichir_messages_main():
    return "\n".join(messages_recus) if messages_recus else "⏳ En attente de messages Unity..."


def rafraichir_statut():
    return get_statut_config()


with gr.Blocks(title="🕹️ Main Controller") as app:

    gr.Markdown("# 🕹️ Main Controller")
    gr.Markdown(
        "Ce controller écoute la config envoyée par Unity au démarrage "
        "et génère automatiquement l'interface de contrôle adaptée au jeu."
    )

    # ── Statut de la config ───────────────────────────────────────────────────
    gr.Markdown("---")
    gr.Markdown("### 📡 Statut")

    statut_box = gr.Markdown("⏳ En attente de la config Unity...")

    with gr.Row():
        btn_rafraichir_statut = gr.Button("🔄 Rafraîchir le statut")
        btn_lancer            = gr.Button("🚀 Lancer le Controller du jeu", variant="primary")

    statut_launch = gr.Textbox(label="Statut du lancement", interactive=False)
    lien_controller = gr.HTML(value="")

    btn_rafraichir_statut.click(
        fn=rafraichir_statut,
        inputs=[],
        outputs=statut_box
    )

    btn_lancer.click(
        fn=lancer_controller,
        inputs=[],
        outputs=[statut_launch, lien_controller]
    )

    # ── Messages reçus de Unity ───────────────────────────────────────────────
    gr.Markdown("---")
    gr.Markdown("### 📨 Messages reçus de Unity (temps réel)")

    messages_box   = gr.Textbox(
        label="Activité du jeu",
        lines=10,
        interactive=False,
        value="⏳ En attente de messages Unity..."
    )
    btn_rafraichir = gr.Button("🔄 Rafraîchir les messages")
    btn_rafraichir.click(
        fn=rafraichir_messages_main,
        inputs=[],
        outputs=messages_box
    )

    # ── Config JSON brute ─────────────────────────────────────────────────────
    gr.Markdown("---")
    gr.Markdown("### 🔧 Config reçue (JSON brut)")

    def voir_config():
        if config_recue:
            return json.dumps(config_recue, indent=2, ensure_ascii=False)
        return "⏳ Aucune config reçue pour l'instant."

    config_box     = gr.Code(label="Config Unity", language="json")
    btn_voir_config = gr.Button("🔍 Voir la config")
    btn_voir_config.click(fn=voir_config, inputs=[], outputs=config_box)


if __name__ == "__main__":
    print("🕹️  Lancement du Main Controller...")
    print(f"🔌 Broker MQTT : {BROKER_HOST}:{BROKER_PORT}")
    print(f"📡 En attente de config Unity sur : {TOPIC_CONFIG}")
    app.launch(server_port=7860)