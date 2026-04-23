"""
unity_stress_test.py
--------------------
Stress test Unity GÉNÉRIQUE — fonctionne avec n'importe quel jeu Unity.
Le comportement est défini par un fichier de config JSON externe.

Usage :
  python unity_stress_test.py --generer-config   # génère des exemples
  python unity_stress_test.py --config config_boules.json
  python unity_stress_test.py --config config_obstacles.json
  python unity_stress_test.py --config mon_nouveau_jeu.json
"""

import json, time, random, argparse, threading
import paho.mqtt.client as mqtt
from datetime import datetime

BROKER_HOST = "devweb.estia.fr"
BROKER_PORT = 1883
USERNAME    = "estia"
PASSWORD    = "*aZ9#r8X7"

fps_recus    = []
cmds_ok      = 0
cmds_ko      = 0

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("jeu/stress/fps")
        print("✅ Connecté — écoute jeu/stress/fps\n")
    else:
        print(f"❌ Erreur connexion : {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == "jeu/stress/fps":
            fps = float(payload.get("fps", 0))
            fps_recus.append(fps)
            h = datetime.now().strftime("%H:%M:%S")
            alerte = " ⚠️ FPS BAS" if fps < 30 else ""
            print(f"  [{h}] FPS : {fps:.1f}{alerte}")
    except Exception as e:
        print(f"❌ Erreur : {e}")

def generer_commande(phase: dict) -> dict:
    """
    Génère une commande depuis la description d'une phase.
    Chaque paramètre peut être :
      - fixe    : { "valeur": 10 }
      - aléatoire : { "min": 2, "max": 20 }  +  "entier": true optionnel
      - choix   : { "choix": [1, 2, 5, 10] }
    """
    commande = {}
    for nom, spec in phase.get("parametres", {}).items():
        if isinstance(spec, (int, float)):
            commande[nom] = spec
        elif isinstance(spec, dict):
            if "valeur" in spec:
                commande[nom] = spec["valeur"]
            elif "min" in spec and "max" in spec:
                val = random.uniform(spec["min"], spec["max"])
                commande[nom] = int(val) if spec.get("entier") else round(val, spec.get("decimales", 1))
            elif "choix" in spec:
                commande[nom] = random.choice(spec["choix"])
    return commande

def lancer_stress(config: dict, client_pub) -> float:
    global cmds_ok, cmds_ko
    topic   = config["topic_commandes"]
    phases  = config["phases"]
    delai_d = config.get("delai_secondes", 0.1)
    nb_tot  = sum(p.get("nb_commandes", 10) for p in phases)

    print(f"🚀 {config['nom']}")
    print(f"   {len(phases)} phases | {nb_tot} commandes | topic : {topic}")
    print(f"\n   ▶️  Lance Unity maintenant si ce n'est pas déjà fait !")
    print(f"   ⏳ Démarrage dans 3 secondes...\n")
    time.sleep(3)

    debut = time.time()
    for idx, phase in enumerate(phases):
        nom  = phase.get("nom", f"Phase {idx+1}")
        desc = phase.get("description", "")
        nb   = phase.get("nb_commandes", 10)
        dl   = phase.get("delai_secondes", delai_d)

        print(f"\n━━━ {nom}" + (f" — {desc}" if desc else ""))

        for i in range(nb):
            cmd = generer_commande(phase)
            cmd["timestamp"] = time.time()
            r = client_pub.publish(topic, json.dumps(cmd), qos=1)
            if r.rc == mqtt.MQTT_ERR_SUCCESS: cmds_ok += 1
            else:                             cmds_ko += 1
            if (i+1) % 20 == 0:
                rec = fps_recus[-5:]
                moy = f"{sum(rec)/len(rec):.1f}" if rec else "N/A"
                print(f"  📤 {i+1}/{nb} | FPS moyen : {moy}")
            time.sleep(dl)

    return time.time() - debut

def afficher_rapport(config: dict, duree: float):
    print("\n" + "="*60)
    print(f"📊 RAPPORT — {config['nom']}")
    print("="*60)
    print(f"  Commandes OK : {cmds_ok} | Ko : {cmds_ko} | Durée : {duree:.1f}s")
    if fps_recus:
        mn, mx, moy = min(fps_recus), max(fps_recus), sum(fps_recus)/len(fps_recus)
        bas = sum(1 for f in fps_recus if f < 30)
        print(f"\n  FPS : min={mn:.1f}  max={mx:.1f}  moy={moy:.1f}")
        print(f"  Chutes < 30 FPS : {bas} fois ({bas/len(fps_recus)*100:.0f}%)")
        if mn >= 60:   print("\n✅ VERDICT : 60+ FPS tout le long — Unity tient parfaitement")
        elif mn >= 30: print(f"\n⚠️  VERDICT : Ralentissements détectés (min {mn:.0f} FPS)")
        else:          print(f"\n❌ VERDICT : Unity surchargé — chutes sous 30 FPS")
    else:
        print("\n⚠️  Aucun FPS reçu — ajoute UnityStressReporter.cs dans la scène")
    print("="*60)

def generer_configs_exemples():
    boules = {
        "nom": "Stress test — Jeu des boules",
        "topic_commandes": "unity/commands",
        "delai_secondes": 0.15,
        "phases": [
            {"nom":"Phase 1 — Montée progressive","description":"Nombre de boules de 2 à 20",
             "nb_commandes":50,"delai_secondes":0.2,
             "parametres":{"taille":{"valeur":1.0},"nombre":{"min":2,"max":20,"entier":True},"rayon_cercle":{"valeur":4.0}}},
            {"nom":"Phase 2 — Boules nombreuses et petites","description":"20 boules minuscules",
             "nb_commandes":30,"delai_secondes":0.1,
             "parametres":{"taille":{"valeur":0.5},"nombre":{"valeur":20},"rayon_cercle":{"valeur":8.0}}},
            {"nom":"Phase 3 — Boules géantes","description":"2 immenses boules",
             "nb_commandes":20,"delai_secondes":0.3,
             "parametres":{"taille":{"valeur":3.0},"nombre":{"valeur":2},"rayon_cercle":{"valeur":2.0}}},
            {"nom":"Phase 4 — Chaos complet","description":"Tout change aléatoirement",
             "nb_commandes":100,"delai_secondes":0.05,
             "parametres":{"taille":{"min":0.5,"max":3.0},"nombre":{"min":2,"max":20,"entier":True},"rayon_cercle":{"min":1.0,"max":10.0}}}
        ]
    }
    obstacles = {
        "nom": "Stress test — Jeu d'obstacles",
        "topic_commandes": "unity/obstacle/commands",
        "delai_secondes": 0.15,
        "phases": [
            {"nom":"Phase 1 — Vitesse progressive","description":"Vitesse de 5 à 20",
             "nb_commandes":40,"delai_secondes":0.2,
             "parametres":{"vitesse":{"min":5.0,"max":20.0},"intervalle":{"valeur":1.5},"points":{"valeur":1}}},
            {"nom":"Phase 2 — Spawn intense","description":"Obstacles très fréquents",
             "nb_commandes":50,"delai_secondes":0.1,
             "parametres":{"vitesse":{"valeur":10.0},"intervalle":{"min":0.2,"max":0.5},"points":{"valeur":2}}},
            {"nom":"Phase 3 — Vitesse max","description":"Obstacles ultra-rapides",
             "nb_commandes":30,"delai_secondes":0.15,
             "parametres":{"vitesse":{"valeur":30.0},"intervalle":{"valeur":1.0},"points":{"valeur":10}}},
            {"nom":"Phase 4 — Chaos total","description":"Tout aléatoire",
             "nb_commandes":80,"delai_secondes":0.05,
             "parametres":{"vitesse":{"min":3.0,"max":30.0},"intervalle":{"min":0.1,"max":3.0},"points":{"choix":[1,2,5,10]}}}
        ]
    }
    with open("config_boules.json","w",encoding="utf-8") as f: json.dump(boules,f,indent=2,ensure_ascii=False)
    with open("config_obstacles.json","w",encoding="utf-8") as f: json.dump(obstacles,f,indent=2,ensure_ascii=False)
    print("✅ config_boules.json et config_obstacles.json générés")
    print("\nPour un nouveau jeu, copie un fichier et adapte :")
    print("  nom              : nom de ton jeu")
    print("  topic_commandes  : le topic MQTT Unity de ton jeu")
    print("  phases.parametres: les paramètres que ton jeu accepte")

def main():
    parser = argparse.ArgumentParser(description="Stress test Unity générique")
    parser.add_argument("--config", type=str, help="Fichier de config JSON")
    parser.add_argument("--generer-config", action="store_true", help="Génère des configs exemples")
    args = parser.parse_args()

    if args.generer_config:
        generer_configs_exemples()
        return

    if not args.config:
        print("❌ Précise un fichier de config : --config config_boules.json")
        print("   Pour des exemples : --generer-config")
        return

    try:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Fichier introuvable : {args.config}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON : {e}")
        return

    client_ecoute = mqtt.Client()
    client_ecoute.username_pw_set(USERNAME, PASSWORD)
    client_ecoute.on_connect = on_connect
    client_ecoute.on_message = on_message
    client_ecoute.connect(BROKER_HOST, BROKER_PORT)
    threading.Thread(target=client_ecoute.loop_forever, daemon=True).start()
    time.sleep(1)

    client_pub = mqtt.Client()
    client_pub.username_pw_set(USERNAME, PASSWORD)
    client_pub.connect(BROKER_HOST, BROKER_PORT)
    client_pub.loop_start()
    time.sleep(0.5)

    duree = lancer_stress(config, client_pub)
    print("\n⏳ Attente des dernières mesures...")
    time.sleep(3)
    client_pub.loop_stop()
    client_ecoute.disconnect()
    afficher_rapport(config, duree)

if __name__ == "__main__":
    main()
